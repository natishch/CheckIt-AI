"""Fact analyst node for evidence synthesis and verification."""

from typing import ClassVar, Literal, cast
from urllib.parse import urlparse

from langchain_core.prompts import ChatPromptTemplate

from check_it_ai.graph.nodes.fact_analyst_check_contradictions import check_contradictions
from check_it_ai.graph.state import AgentState
from check_it_ai.utils.logging import setup_logger
from src.check_it_ai.config import settings
from src.check_it_ai.llm.providers import get_analyst_llm
from src.check_it_ai.types.analyst import ExtractedClaims, SingleEvaluation, VerdictResult
from src.check_it_ai.types.evidence import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceVerdict,
    Finding,
)
from src.check_it_ai.types.search import SearchResult

logger = setup_logger(__name__)


# =============================================================================
# Claim Extraction Prompt
# =============================================================================
CLAIM_EXTRACTION_SYSTEM = """You are a fact-checking assistant. Your task is to decompose a user's query into atomic, verifiable claims.

Rules:
1. Extract 1-5 distinct factual claims from the query
2. Each claim should be independently verifiable
3. Remove opinions, questions, and subjective statements
4. Keep claims concise but complete
5. If the query is already a single atomic claim, return it as-is

Examples:
- Input: "Is it true that Einstein invented the light bulb and won a Nobel Prize?"
  Output: ["Einstein invented the light bulb", "Einstein won a Nobel Prize"]

- Input: "The Earth is flat"
  Output: ["The Earth is flat"]

- Input: "Did Apple buy Twitter for $50 billion in 2023?"
  Output: ["Apple bought Twitter", "The acquisition price was $50 billion", "The acquisition occurred in 2023"]
"""


def extract_claims(user_query: str) -> list[str]:
    """Extract atomic, verifiable claims from a user query using LLM.

    Args:
        user_query: The user's fact-checking query.

    Returns:
        List of 1-5 atomic claims extracted from the query.
        Falls back to [user_query] if extraction fails.
    """
    try:
        llm = get_analyst_llm(settings)
        structured_llm = llm.with_structured_output(ExtractedClaims)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CLAIM_EXTRACTION_SYSTEM),
                ("human", "Extract verifiable claims from: {query}"),
            ]
        )

        chain = prompt | structured_llm
        result = cast(ExtractedClaims, chain.invoke({"query": user_query}))

        logger.info(f"Extracted {len(result.claims)} claims from query: {result.claims}")
        return result.claims

    except Exception as e:
        logger.warning(f"Claim extraction failed, using original query: {e}")
        return [user_query]


# =============================================================================
# Per-Pair Evidence Evaluation
# =============================================================================
EVIDENCE_EVAL_SYSTEM = """You are a Fact Analyst evaluating whether a SOURCE SNIPPET supports a CLAIM.

EVALUATION CRITERIA:
- SUPPORTED: The snippet EXPLICITLY confirms the claim is true
- NOT_SUPPORTED: The snippet EXPLICITLY contradicts or refutes the claim
- IRRELEVANT: The snippet doesn't address the claim or lacks sufficient detail

Consider the SOURCE_CREDIBILITY score (0.0-1.0) when assessing confidence:
- Higher credibility sources (0.7+) warrant higher confidence
- Lower credibility sources (below 0.5) warrant lower confidence

Be conservative: only mark SUPPORTED/NOT_SUPPORTED if the evidence is clear."""


def evaluate_single_pair(
    claim: str,
    snippet: str,
    credibility: float,
) -> SingleEvaluation:
    """Evaluate a single (claim, snippet) pair using LLM.

    Args:
        claim: The atomic claim to verify.
        snippet: The evidence snippet from a search result.
        credibility: Normalized credibility score (0.0-1.0) of the source.

    Returns:
        SingleEvaluation with verdict, confidence, and reasoning.
    """
    try:
        llm = get_analyst_llm(settings)
        structured_llm = llm.with_structured_output(SingleEvaluation)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", EVIDENCE_EVAL_SYSTEM),
                ("human", "CLAIM: {claim}\nSNIPPET: {snippet}\nSOURCE_CREDIBILITY: {credibility}"),
            ]
        )

        chain = prompt | structured_llm
        result = cast(
            SingleEvaluation,
            chain.invoke(
                {
                    "claim": claim,
                    "snippet": snippet,
                    "credibility": credibility,
                }
            ),
        )

        logger.debug(
            f"Evaluation: {result.verdict} ({result.confidence}) - {result.reasoning[:50]}..."
        )
        return result

    except Exception as e:
        logger.warning(f"Per-pair evaluation failed: {e}")
        return SingleEvaluation(
            verdict="IRRELEVANT",
            confidence=0.5,
            reasoning=f"Evaluation error: {str(e)[:50]}",
        )


# =============================================================================
# Verdict Aggregation Functions
# =============================================================================
def aggregate_verdicts(
    evaluations: list[tuple[str, SingleEvaluation]],
) -> tuple[EvidenceVerdict, list[str]]:
    """Aggregate individual verdicts into final verdict for a claim.

    Args:
        evaluations: List of (evidence_id, SingleEvaluation) tuples.

    Returns:
        Tuple of (final_verdict, list of relevant evidence IDs).
    """
    supported_ids: list[str] = []
    not_supported_ids: list[str] = []

    for evidence_id, eval_result in evaluations:
        if eval_result.verdict == "SUPPORTED":
            supported_ids.append(evidence_id)
        elif eval_result.verdict == "NOT_SUPPORTED":
            not_supported_ids.append(evidence_id)
        # IRRELEVANT items are ignored

    has_support = len(supported_ids) > 0
    has_contradiction = len(not_supported_ids) > 0

    # Conflict detection: both support and contradiction present
    if has_support and has_contradiction:
        return EvidenceVerdict.CONTESTED, supported_ids + not_supported_ids

    if has_support:
        return EvidenceVerdict.SUPPORTED, supported_ids

    if has_contradiction:
        return EvidenceVerdict.NOT_SUPPORTED, not_supported_ids

    return EvidenceVerdict.INSUFFICIENT, []


def synthesize_overall_verdict(findings: list[Finding]) -> EvidenceVerdict:
    """Synthesize overall verdict from all claim findings.

    Priority order: CONTESTED > NOT_SUPPORTED > SUPPORTED > INSUFFICIENT

    Args:
        findings: List of Finding objects, one per claim.

    Returns:
        The overall EvidenceVerdict for the query.
    """
    if not findings:
        return EvidenceVerdict.INSUFFICIENT

    verdicts = [f.verdict for f in findings]

    # Priority: CONTESTED > NOT_SUPPORTED > SUPPORTED > INSUFFICIENT
    if EvidenceVerdict.CONTESTED in verdicts:
        return EvidenceVerdict.CONTESTED

    if EvidenceVerdict.NOT_SUPPORTED in verdicts:
        return EvidenceVerdict.NOT_SUPPORTED

    if all(v == EvidenceVerdict.SUPPORTED for v in verdicts):
        return EvidenceVerdict.SUPPORTED

    return EvidenceVerdict.INSUFFICIENT


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

    # Mapping from integer scores to normalized floats (0.0-1.0) for LLM prompts
    _SCORE_TO_NORMALIZED: ClassVar[dict[int, float]] = {
        SCORE_FACT_CHECKER: 0.95,
        SCORE_GOV_EDU: 0.95,
        SCORE_NEWS_ORG: 0.70,
        SCORE_GENERIC: 0.50,
        SCORE_LOW_QUALITY: 0.30,
    }

    @classmethod
    def score_normalized(cls, result: SearchResult) -> float:
        """
        Return credibility as a normalized float (0.0-1.0) for LLM prompts.

        This is useful when passing source credibility to the LLM for
        confidence weighting in evidence evaluation.
        """
        raw_score = cls.score(result)
        return cls._SCORE_TO_NORMALIZED.get(raw_score, 0.30)


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
            i
            for i, (_, score) in enumerate(scored_results)
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

        try:
            llm = get_analyst_llm(settings)
            structured_llm = llm.with_structured_output(VerdictResult)
            prompt = ChatPromptTemplate.from_template(cls.VERDICT_PROMPT)

            chain = prompt | structured_llm
            result = cast(VerdictResult, chain.invoke({"query": query, "snippets": snippets_text}))

            logger.info(
                f"LLM Verdict: {result.verdict} (Confidence: {result.confidence}) - {result.reasoning}"
            )

            # Optional: Enforce a confidence threshold
            if result.confidence < 0.5:
                return "insufficient"

            return result.verdict

        except Exception as e:
            logger.error(f"LLM verdict check failed: {e}")
            return "insufficient"


def fact_analyst_node(state: AgentState) -> dict:
    """Analyze search results and build evidence bundle.

    Pipeline:
    1. Extract atomic claims from user query
    2. Score source credibility
    3. Build evidence items
    4. Evaluate each (claim, evidence) pair
    5. Aggregate into findings
    6. Synthesize overall verdict
    """
    logger.info(
        f"Analyzing {len(state.search_results)} search results for query: '{state.user_query}'"
    )

    if not state.search_results:
        logger.warning("No search results to analyze.")
        return {
            "evidence_bundle": EvidenceBundle(
                items=[],
                findings=[],
                overall_verdict=EvidenceVerdict.INSUFFICIENT,
            )
        }

    # STAGE 1: Extract atomic claims
    claims = extract_claims(state.user_query)
    logger.info(f"Extracted {len(claims)} claims: {claims}")

    # STAGE 2: Score Results
    scored_results: list[tuple[SearchResult, int, float]] = []
    for result in state.search_results:
        score = SourceCredibilityScorer.score(result)
        credibility = SourceCredibilityScorer.score_normalized(result)
        scored_results.append((result, score, credibility))

    # Sort by score descending
    scored_results.sort(key=lambda x: x[1], reverse=True)

    # STAGE 3: Build Evidence Items
    evidence_items: list[EvidenceItem] = []
    for idx, (result, _score, _cred) in enumerate(scored_results, 1):
        item = EvidenceItem(
            id=f"E{idx}",
            title=result.title,
            snippet=result.snippet,
            url=result.url,
            display_domain=result.display_domain,
        )
        evidence_items.append(item)

    # STAGE 4: Evaluate each (claim, evidence) pair
    # Limit to top 5 evidence items to control API costs
    top_evidence = evidence_items[:5]
    top_scored = scored_results[:5]

    findings: list[Finding] = []

    for claim in claims:
        evaluations: list[tuple[str, SingleEvaluation]] = []

        for item, (_, _, credibility) in zip(top_evidence, top_scored, strict=False):
            eval_result = evaluate_single_pair(
                claim=claim,
                snippet=item.snippet,
                credibility=credibility,
            )
            evaluations.append((item.id, eval_result))

        # STAGE 5: Aggregate verdicts for this claim
        final_verdict, evidence_ids = aggregate_verdicts(evaluations)

        findings.append(
            Finding(
                claim=claim,
                verdict=final_verdict,
                evidence_ids=evidence_ids,
            )
        )

        logger.debug(f"Claim '{claim[:50]}...' → {final_verdict.value} (evidence: {evidence_ids})")

    # STAGE 6: Synthesize overall verdict
    overall_verdict = synthesize_overall_verdict(findings)

    # Build Bundle (PRESERVED structure)
    bundle = EvidenceBundle(
        items=evidence_items,
        findings=findings,
        overall_verdict=overall_verdict,
    )

    # Update Metadata
    analysis_metadata = {
        "claims_extracted": len(claims),
        "total_evidence_count": len(evidence_items),
        "findings_count": len(findings),
        "overall_verdict": overall_verdict.value,
        "avg_credibility_score": sum(s for _, s, _ in scored_results) / len(scored_results)
        if scored_results
        else 0,
        "top_source_domain": scored_results[0][0].display_domain if scored_results else None,
    }

    new_metadata = state.run_metadata.copy()
    new_metadata["fact_analyst"] = analysis_metadata

    logger.info(f"Analysis complete. Verdict: {overall_verdict.value}")

    return {
        "evidence_bundle": bundle,
        "run_metadata": new_metadata,
    }
