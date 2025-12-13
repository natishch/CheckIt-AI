import os
from typing import cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from check_it_ai.utils.logging import setup_logger
from src.check_it_ai.types.evidence import EvidenceItem

logger = setup_logger(__name__)


class ContradictionResult(BaseModel):
    """Schema for contradiction check result."""

    reasoning: str = Field(
        ..., description="Brief explanation of the contradiction or lack thereof"
    )
    is_contradiction: bool = Field(
        ..., description="Whether a significant factual contradiction exists"
    )
    confidence: int = Field(..., description="Confidence score between 0 and 10")


CONTRADICTION_PROMPT = """
    You are an expert fact-checker. Analyze the following evidence snippets for significant factual contradictions regarding the user's claim.

    User Claim: "{query}"

    High-Quality Evidence Snippets:
    {snippets}

    Task:
    1. Identify if there are any SIGNIFICANT factual contradictions between these sources (e.g. different dates, numbers, or outcomes).
    2. Ignore minor differences in wording or perspective.
    """


def check_contradictions(
    evidence_items: list[EvidenceItem],
    query: str,
) -> bool:
    """
    Detect contradictions using an LLM on high-quality sources.
    Returns True if a significant contradiction is found with high confidence.
    """
    # 1. Filter for high-quality items only
    # Note: We assume evidence_items passed here correspond to high scores,
    # but since we only have items, we might need to rely on the caller to filter
    # or re-score implicitly. To stay efficient, we'll trust the caller to pass
    # relevant items or we filter by checking domains again if needed.
    # For now, let's assume the caller filters the list.

    if len(evidence_items) < 2:
        return False

    # 2. Check for API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not found. Skipping LLM contradiction check.")
        return False

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        structured_llm = llm.with_structured_output(ContradictionResult)
        prompt = ChatPromptTemplate.from_template(CONTRADICTION_PROMPT)

        snippets_text = "\n".join(
            [
                f"- Source {i + 1} ({item.display_domain}): {item.snippet}"
                for i, item in enumerate(evidence_items)
            ]
        )

        chain = prompt | structured_llm
        result = cast(
            ContradictionResult, chain.invoke({"query": query, "snippets": snippets_text})
        )

        # Logic: Yes + Confidence >= 8
        if result.is_contradiction and result.confidence >= 8:
            logger.info(f"Contradiction detected by LLM (Confidence: {result.confidence})")
            return True

    except Exception as e:
        logger.error(f"LLM contradiction check failed: {e}")
        return False

    return False
