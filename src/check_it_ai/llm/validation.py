"""Citation Validation and Confidence Calculation for Writer Node.

This module provides utilities for:
1. Extracting and validating citations from LLM responses
2. Calculating hybrid confidence scores based on evidence and LLM self-assessment
"""

from __future__ import annotations

import re

from src.check_it_ai.types.evidence import EvidenceBundle, EvidenceVerdict

# Citation pattern: matches [E1], [E2], [E10], etc.
CITATION_PATTERN = re.compile(r"\[E(\d+)\]")


def extract_citation_ids(text: str) -> set[str]:
    """Extract all citation IDs from text.

    Args:
        text: The text to search for citations.

    Returns:
        A set of citation IDs found (e.g., {"E1", "E2", "E10"}).
        Returns empty set if text is empty or None.

    Examples:
        >>> extract_citation_ids("According to [E1] and [E2]...")
        {"E1", "E2"}
        >>> extract_citation_ids("Text [E1] more [E1] text")
        {"E1"}  # Deduplicated
        >>> extract_citation_ids("No citations here")
        set()
    """
    if not text:
        return set()

    matches = CITATION_PATTERN.findall(text)
    return {f"E{num}" for num in matches}


def validate_citations(
    answer_text: str,
    evidence_bundle: EvidenceBundle | None,
) -> dict[str, bool | set[str]]:
    """Validate that all citations in the answer exist in the evidence bundle.

    Args:
        answer_text: The LLM-generated answer text containing citations.
        evidence_bundle: The evidence bundle with available evidence items.

    Returns:
        A dict with validation results:
        {
            "is_valid": bool,           # True if all citations are valid and at least one exists
            "cited_ids": set[str],      # All [E#] found in text
            "valid_ids": set[str],      # Citations that exist in bundle
            "invalid_ids": set[str],    # Hallucinated citations (not in bundle)
            "available_ids": set[str],  # All IDs available in the bundle
        }
    """
    # Extract all [E#] patterns from text
    cited_ids = extract_citation_ids(answer_text)

    # Get available IDs from bundle
    if evidence_bundle and evidence_bundle.evidence_items:
        available_ids = {item.id for item in evidence_bundle.evidence_items}
    else:
        available_ids = set()

    # Partition into valid and invalid
    valid_ids = cited_ids & available_ids
    invalid_ids = cited_ids - available_ids

    # Is valid if: no invalid citations AND at least one citation exists
    is_valid = len(invalid_ids) == 0 and len(cited_ids) > 0

    return {
        "is_valid": is_valid,
        "cited_ids": cited_ids,
        "valid_ids": valid_ids,
        "invalid_ids": invalid_ids,
        "available_ids": available_ids,
    }


def get_verdict_baseline(verdict: EvidenceVerdict) -> float:
    """Get the baseline confidence score for a given verdict.

    Args:
        verdict: The evidence verdict enum.

    Returns:
        A baseline confidence score between 0 and 1.
    """
    baselines = {
        EvidenceVerdict.SUPPORTED: 0.8,
        EvidenceVerdict.NOT_SUPPORTED: 0.75,  # High confidence in refutation
        EvidenceVerdict.CONTESTED: 0.5,
        EvidenceVerdict.INSUFFICIENT: 0.25,
    }
    return baselines.get(verdict, 0.5)


def calculate_confidence(
    llm_confidence: float,
    evidence_bundle: EvidenceBundle | None,
    cited_ids: set[str],
) -> float:
    """Calculate final confidence using hybrid approach.

    The hybrid approach combines:
    1. Verdict-derived baseline (60% weight, or 100% if LLM didn't provide confidence)
    2. LLM self-assessment (40% weight, if provided)
    3. Objective signal modifiers (source count, contested findings)

    Args:
        llm_confidence: The LLM's self-assessed confidence (0.0-1.0), or -1.0 if not provided.
        evidence_bundle: The evidence bundle with verdict and findings.
        cited_ids: Set of evidence IDs cited in the answer.

    Returns:
        Final confidence score between 0.0 and 1.0.
    """
    # Handle missing bundle
    if not evidence_bundle:
        if llm_confidence < 0:
            return 0.3  # Conservative default
        return min(0.3, llm_confidence)

    # Step 1: Get verdict-derived baseline
    overall_verdict = evidence_bundle.overall_verdict
    baseline = get_verdict_baseline(overall_verdict)

    # Step 2: Blend with LLM confidence
    # If LLM didn't provide confidence (sentinel -1.0), use baseline only
    if llm_confidence < 0:
        blended = baseline
    else:
        # Ensure llm_confidence is in valid range
        llm_conf = max(0.0, min(1.0, llm_confidence))
        blended = (baseline * 0.6) + (llm_conf * 0.4)

    # Step 3: Apply objective modifiers based on source count
    num_sources = len(cited_ids)

    if num_sources == 0:
        blended = min(blended, 0.3)
    elif num_sources == 1:
        blended = min(blended, 0.7)
    elif num_sources >= 3:
        blended = min(blended + 0.05, 1.0)

    # Step 4: Check for contested findings - cap at 0.6
    if evidence_bundle.findings:
        if any(f.verdict == EvidenceVerdict.CONTESTED for f in evidence_bundle.findings):
            blended = min(blended, 0.6)

    # Ensure final value is in valid range
    return max(0.0, min(1.0, blended))


def build_hallucination_correction_prompt(
    invalid_ids: set[str],
    available_ids: set[str],
) -> str:
    """Build a correction prompt for hallucinated citations.

    Args:
        invalid_ids: Set of citation IDs that don't exist in the bundle.
        available_ids: Set of valid citation IDs from the bundle.

    Returns:
        A correction prompt string to send to the LLM.
    """
    return f"""Your previous response contained invalid citations: {sorted(invalid_ids)}

    These evidence IDs do NOT exist. The only valid evidence IDs are: {sorted(available_ids)}

    Please regenerate your response using ONLY the valid evidence IDs listed above.
    Do not use any citation that is not in the valid list.

    Remember to output a JSON object with: answer, confidence, evidence_ids, limitations"""
