"""Fact analyst node for evidence synthesis and verification."""

import os
from typing import ClassVar, Literal, cast
from urllib.parse import urlparse

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from check_it_ai.graph.nodes.fact_analyst_check_contradictions import check_contradictions
from check_it_ai.graph.state import AgentState
from check_it_ai.types.schemas import EvidenceBundle, EvidenceItem, Finding, SearchResult
from check_it_ai.utils.logging import setup_logger

logger = setup_logger(__name__)


class SourceCredibilityScorer:
    """Assigns credibility scores to search results based on source type and domain."""

    # Default Scores
    SCORE_FACT_CHECKER: ClassVar[int] = 10
    SCORE_GOV_EDU: ClassVar[int] = 8
    SCORE_NEWS_ORG: ClassVar[int] = 6
    SCORE_GENERIC: ClassVar[int] = 3
    SCORE_LOW_QUALITY: ClassVar[int] = 2

    # Reputable news domains (can be expanded via config later)
    NEWS_DOMAINS: ClassVar[set[str]] = {
        "reuters.com",
        "apnews.com",
        "bbc.com",
        "bbc.co.uk",
        "npr.org",
        "theguardian.com",
        "nytimes.com",
        "wsj.com",
        "washingtonpost.com",
        "bloomberg.com",
        "cnn.com",
        "dw.com",
        "france24.com",
        "wikipedia.org",
    }

    @classmethod
    def score(cls, result: SearchResult) -> int:
        """Calculate credibility score for a single search result."""
        # Tier 1: Professional Fact-Checkers (detected by prefix from tools)
        if "[FACT-CHECK]" in result.title or "fact check" in result.title.lower():
            return cls.SCORE_FACT_CHECKER

        domain = result.display_domain.lower()
        # Parse netloc for more robust matching (e.g. "www.bbc.co.uk")
        try:
            parsed_url = urlparse(str(result.url))
            netloc = parsed_url.netloc.lower()
        except Exception:
            netloc = domain

        # Tier 2: Government and Education
        if domain.endswith(".gov") or domain.endswith(".edu"):
            return cls.SCORE_GOV_EDU
        if ".gov." in domain or ".edu." in domain:  # International (e.g. .gov.uk)
            return cls.SCORE_GOV_EDU

        # Tier 3: Reputable News
        # Check if known news domain appears in the result's domain
        for news_domain in cls.NEWS_DOMAINS:
            if news_domain in domain or news_domain in netloc:
                return cls.SCORE_NEWS_ORG

        # Tier 4: Generic / Tier 5: Low Quality (Placeholder for now)
        return cls.SCORE_GENERIC


class VerdictResult(BaseModel):
    verdict: Literal["supported", "not_supported", "contested", "insufficient"]
    reasoning: str
    confidence: float


class ContentAnalyzer:
    """Analyzes text content for dates, entities, and contradictions using LLM."""

    VERDICT_PROMPT = """
    You are an expert fact-checker. Compare the User's Claim against the provided Evidence.

    User Claim: "{query}"

    Evidence Snippets:
    {snippets}

    Task:
    Determine if the evidence supports, refutes, or is insufficient to judge the claim.

    Output Verdict:
    - "supported": Evidence confirms the claim is true.
    - "not_supported": Evidence confirms the claim is false.
    - "contested": Evidence is conflicting (some supports, some refutes).
    - "insufficient": Evidence is not relevant or verified enough.

    Provide a brief reason and a confidence score (0.0-1.0).
    """

    @classmethod
    def determine_verdict(
        cls,
        evidence_items: list[EvidenceItem],
        scored_results: list[tuple[SearchResult, int]],
        query: str,
    ) -> Literal["supported", "not_supported", "contested", "insufficient"]:
        """Determine overall verdict based on scores and content analysis."""
        if not evidence_items:
            return "insufficient"

        # 1. Check for Contradictions via LLM
        # Filter high-quality evidence for the check
        high_quality_indices = [
            i for i, (_, score) in enumerate(scored_results)
            if score >= SourceCredibilityScorer.SCORE_GOV_EDU
        ]

        high_quality_items = [evidence_items[i] for i in high_quality_indices]

        if check_contradictions(high_quality_items, query):
            return "contested"

        # 2. LLM Verification (Claim vs. Evidence)
        # We use the top 5 most credible items for the LLM check
        top_items = evidence_items[:5]
        snippets_text = "\n".join(
            [f"- [{item.display_domain}] {item.snippet}" for item in top_items]
        )

        # Check for API Key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY missing. Returning 'insufficient'.")
            return "insufficient"

        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            structured_llm = llm.with_structured_output(VerdictResult)
            prompt = ChatPromptTemplate.from_template(cls.VERDICT_PROMPT)

            chain = prompt | structured_llm
            result = cast(VerdictResult, chain.invoke({
                "query": query,
                "snippets": snippets_text
            }))

            logger.info(f"LLM Verdict: {result.verdict} (Confidence: {result.confidence}) - {result.reasoning}")

            # Optional: Enforce a confidence threshold
            if result.confidence < 0.5:
                return "insufficient"

            return result.verdict

        except Exception as e:
            logger.error(f"LLM verdict check failed: {e}")
            return "insufficient"


def analyze_facts(state: AgentState) -> dict:
    """
    Analyze search results and build evidence bundle.
    """
    logger.info(f"Analyzing {len(state.search_results)} search results for query: '{state.user_query}'")

    if not state.search_results:
        logger.warning("No search results to analyze.")
        return {
            "evidence_bundle": EvidenceBundle(
                items=[],
                findings=[],
                overall_verdict="insufficient",
            )
        }

    # 1. Score Results
    scored_results = []
    for result in state.search_results:
        score = SourceCredibilityScorer.score(result)
        scored_results.append((result, score))

    # Sort by score descending
    scored_results.sort(key=lambda x: x[1], reverse=True)

    # 2. Build Evidence Items
    evidence_items: list[EvidenceItem] = []
    evidence_ids: list[str] = []

    for idx, (result, _score) in enumerate(scored_results, 1):
        e_id = f"E{idx}"
        item = EvidenceItem(
            id=e_id,
            title=result.title,
            snippet=result.snippet,
            url=result.url,
            display_domain=result.display_domain,
        )
        evidence_items.append(item)
        evidence_ids.append(e_id)

    # 3. Determine Verdict
    verdict = ContentAnalyzer.determine_verdict(evidence_items, scored_results, state.user_query)

    # 4. Create Finding
    finding = Finding(
        claim=state.user_query,
        verdict=verdict,
        evidence_ids=evidence_ids,
    )

    # 5. Create Bundle
    bundle = EvidenceBundle(
        items=evidence_items,
        findings=[finding],
        overall_verdict=verdict,
    )

    # 6. Update Metadata
    analysis_metadata = {
        "total_evidence_count": len(evidence_items),
        "avg_credibility_score": sum(s for _, s in scored_results) / len(scored_results) if scored_results else 0,
        "contradiction_detected": verdict == "contested",
        "top_source_domain": scored_results[0][0].display_domain if scored_results else None,
    }

    # Merge with existing run_metadata
    new_metadata = state.run_metadata.copy()
    new_metadata["fact_analyst"] = analysis_metadata

    logger.info(f"Analysis complete. Verdict: {verdict}")

    return {
        "evidence_bundle": bundle,
        "run_metadata": new_metadata
    }
