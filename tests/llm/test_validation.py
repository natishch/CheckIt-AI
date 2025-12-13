"""Tests for citation validation and confidence calculation.

These tests verify that:
1. Citations are correctly extracted from text
2. Citations are validated against the evidence bundle
3. Confidence scores are calculated using the hybrid approach
"""

import pytest

from src.check_it_ai.llm.validation import (
    build_hallucination_correction_prompt,
    calculate_confidence,
    extract_citation_ids,
    validate_citations,
)
from src.check_it_ai.types.evidence import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceVerdict,
    Finding,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_evidence_bundle() -> EvidenceBundle:
    """Create a sample evidence bundle with E1, E2, E3."""
    return EvidenceBundle(
        evidence_items=[
            EvidenceItem(
                id="E1",
                title="Source 1",
                snippet="Snippet 1",
                url="https://example.com/1",
            ),
            EvidenceItem(
                id="E2",
                title="Source 2",
                snippet="Snippet 2",
                url="https://example.com/2",
            ),
            EvidenceItem(
                id="E3",
                title="Source 3",
                snippet="Snippet 3",
                url="https://example.com/3",
            ),
        ],
        overall_verdict=EvidenceVerdict.SUPPORTED,
    )


@pytest.fixture
def contested_bundle() -> EvidenceBundle:
    """Create an evidence bundle with contested findings."""
    return EvidenceBundle(
        evidence_items=[
            EvidenceItem(
                id="E1",
                title="Source 1",
                snippet="Snippet 1",
                url="https://example.com/1",
            ),
            EvidenceItem(
                id="E2",
                title="Source 2",
                snippet="Snippet 2",
                url="https://example.com/2",
            ),
        ],
        findings=[
            Finding(
                claim="Test claim",
                verdict=EvidenceVerdict.CONTESTED,
                evidence_ids=["E1", "E2"],
            ),
        ],
        overall_verdict=EvidenceVerdict.CONTESTED,
    )


# =============================================================================
# Test Citation Extraction
# =============================================================================


def test_extract_single_citation():
    """Should extract a single citation."""
    result = extract_citation_ids("According to [E1], this is true.")
    assert result == {"E1"}


def test_extract_multiple_citations():
    """Should extract multiple citations."""
    result = extract_citation_ids("Sources [E1] and [E2] agree on this point.")
    assert result == {"E1", "E2"}


def test_extract_duplicate_citations():
    """Should deduplicate repeated citations."""
    result = extract_citation_ids("Both [E1] and again [E1] mention this.")
    assert result == {"E1"}


def test_extract_no_citations():
    """Should return empty set for text without citations."""
    result = extract_citation_ids("This text has no citations.")
    assert result == set()


def test_extract_malformed_citations():
    """Should ignore malformed citations."""
    result = extract_citation_ids("[E] [e1] [E1a] [E-1] E1 (E1)")
    assert result == set()


def test_extract_empty_text():
    """Should handle empty or None text."""
    assert extract_citation_ids("") == set()
    assert extract_citation_ids(None) == set()


def test_extract_high_numbered_citation():
    """Should extract double-digit citation IDs."""
    result = extract_citation_ids("According to [E10] and [E99]...")
    assert result == {"E10", "E99"}


def test_extract_citations_in_json():
    """Should extract citations embedded in JSON-like text."""
    text = '{"answer": "The claim is supported [E1][E2].", "confidence": 0.9}'
    result = extract_citation_ids(text)
    assert result == {"E1", "E2"}


# =============================================================================
# Test Citation Validation
# =============================================================================


def test_validate_all_citations_exist(sample_evidence_bundle: EvidenceBundle):
    """Should report valid when all citations exist in bundle."""
    result = validate_citations("According to [E1] and [E2]...", sample_evidence_bundle)

    assert result["is_valid"] is True
    assert result["cited_ids"] == {"E1", "E2"}
    assert result["valid_ids"] == {"E1", "E2"}
    assert result["invalid_ids"] == set()
    assert result["available_ids"] == {"E1", "E2", "E3"}


def test_validate_hallucinated_citation(sample_evidence_bundle: EvidenceBundle):
    """Should detect citation that doesn't exist in bundle."""
    result = validate_citations("According to [E99]...", sample_evidence_bundle)

    assert result["is_valid"] is False
    assert result["cited_ids"] == {"E99"}
    assert result["invalid_ids"] == {"E99"}
    assert result["valid_ids"] == set()


def test_validate_partial_hallucination(sample_evidence_bundle: EvidenceBundle):
    """Should detect when some citations are valid and some are hallucinated."""
    result = validate_citations("According to [E1] and [E99]...", sample_evidence_bundle)

    assert result["is_valid"] is False
    assert result["cited_ids"] == {"E1", "E99"}
    assert result["valid_ids"] == {"E1"}
    assert result["invalid_ids"] == {"E99"}


def test_validate_no_citations(sample_evidence_bundle: EvidenceBundle):
    """Should report invalid when no citations are present."""
    result = validate_citations("No citations here.", sample_evidence_bundle)

    assert result["is_valid"] is False
    assert result["cited_ids"] == set()


def test_validate_empty_bundle():
    """Should handle empty or None bundle."""
    result = validate_citations("According to [E1]...", None)

    assert result["is_valid"] is False
    assert result["invalid_ids"] == {"E1"}
    assert result["available_ids"] == set()


def test_validate_empty_evidence_items():
    """Should handle bundle with empty evidence items."""
    bundle = EvidenceBundle(evidence_items=[])
    result = validate_citations("According to [E1]...", bundle)

    assert result["is_valid"] is False
    assert result["invalid_ids"] == {"E1"}


# =============================================================================
# Test Confidence Calculation
# =============================================================================


def test_confidence_supported_multiple_sources(sample_evidence_bundle: EvidenceBundle):
    """Supported verdict with 3+ sources should give high confidence."""
    confidence = calculate_confidence(
        llm_confidence=0.9,
        evidence_bundle=sample_evidence_bundle,
        cited_ids={"E1", "E2", "E3"},
    )
    # Baseline 0.8 * 0.6 + 0.9 * 0.4 = 0.48 + 0.36 = 0.84, +0.05 for 3 sources = 0.89
    assert confidence >= 0.8


def test_confidence_contested_verdict(contested_bundle: EvidenceBundle):
    """Contested verdict should cap confidence at 0.6."""
    confidence = calculate_confidence(
        llm_confidence=0.9,
        evidence_bundle=contested_bundle,
        cited_ids={"E1", "E2"},
    )
    assert confidence <= 0.6


def test_confidence_insufficient_verdict():
    """Insufficient verdict should give low confidence."""
    bundle = EvidenceBundle(
        evidence_items=[
            EvidenceItem(
                id="E1",
                title="Source 1",
                snippet="Snippet",
                url="https://example.com/1",
            ),
        ],
        overall_verdict=EvidenceVerdict.INSUFFICIENT,
    )
    confidence = calculate_confidence(
        llm_confidence=0.5,
        evidence_bundle=bundle,
        cited_ids={"E1"},
    )
    # Baseline 0.25 * 0.6 + 0.5 * 0.4 = 0.15 + 0.2 = 0.35
    # Single source cap: 0.7, so 0.35 is below that
    assert confidence <= 0.4


def test_confidence_single_source_cap():
    """Single source should cap confidence at 0.7."""
    bundle = EvidenceBundle(
        evidence_items=[
            EvidenceItem(
                id="E1",
                title="Source 1",
                snippet="Snippet",
                url="https://example.com/1",
            ),
        ],
        overall_verdict=EvidenceVerdict.SUPPORTED,
    )
    confidence = calculate_confidence(
        llm_confidence=1.0,
        evidence_bundle=bundle,
        cited_ids={"E1"},
    )
    # Even with high LLM confidence, single source caps at 0.7
    assert confidence <= 0.7


def test_confidence_no_citations():
    """No citations should cap confidence at 0.3."""
    bundle = EvidenceBundle(
        evidence_items=[
            EvidenceItem(
                id="E1",
                title="Source 1",
                snippet="Snippet",
                url="https://example.com/1",
            ),
        ],
        overall_verdict=EvidenceVerdict.SUPPORTED,
    )
    confidence = calculate_confidence(
        llm_confidence=0.9,
        evidence_bundle=bundle,
        cited_ids=set(),  # No citations
    )
    assert confidence <= 0.3


def test_confidence_no_bundle():
    """Missing bundle should give very low confidence."""
    confidence = calculate_confidence(
        llm_confidence=0.9,
        evidence_bundle=None,
        cited_ids={"E1"},
    )
    assert confidence <= 0.3


def test_confidence_clamps_llm_confidence():
    """Should handle out-of-range LLM confidence values."""
    bundle = EvidenceBundle(
        evidence_items=[
            EvidenceItem(
                id="E1",
                title="Source 1",
                snippet="Snippet",
                url="https://example.com/1",
            ),
        ],
        overall_verdict=EvidenceVerdict.SUPPORTED,
    )

    # Test negative
    confidence = calculate_confidence(-0.5, bundle, {"E1"})
    assert 0.0 <= confidence <= 1.0

    # Test above 1.0
    confidence = calculate_confidence(1.5, bundle, {"E1"})
    assert 0.0 <= confidence <= 1.0


def test_confidence_always_in_range(sample_evidence_bundle: EvidenceBundle):
    """Confidence should always be between 0.0 and 1.0."""
    for llm_conf in [0.0, 0.3, 0.5, 0.7, 1.0]:
        for cited in [set(), {"E1"}, {"E1", "E2"}, {"E1", "E2", "E3"}]:
            confidence = calculate_confidence(llm_conf, sample_evidence_bundle, cited)
            assert 0.0 <= confidence <= 1.0, f"Out of range for llm={llm_conf}, cited={cited}"


# =============================================================================
# Test Hallucination Correction Prompt
# =============================================================================


def test_correction_prompt_includes_invalid_ids():
    """Correction prompt should list invalid IDs."""
    prompt = build_hallucination_correction_prompt(
        invalid_ids={"E99", "E100"},
        available_ids={"E1", "E2", "E3"},
    )
    assert "E99" in prompt
    assert "E100" in prompt


def test_correction_prompt_includes_available_ids():
    """Correction prompt should list available IDs."""
    prompt = build_hallucination_correction_prompt(
        invalid_ids={"E99"},
        available_ids={"E1", "E2", "E3"},
    )
    assert "E1" in prompt
    assert "E2" in prompt
    assert "E3" in prompt


def test_correction_prompt_requests_json():
    """Correction prompt should remind about JSON output format."""
    prompt = build_hallucination_correction_prompt(
        invalid_ids={"E99"},
        available_ids={"E1"},
    )
    assert "JSON" in prompt


def test_correction_prompt_warns_about_invalid():
    """Correction prompt should clearly indicate invalid citations."""
    prompt = build_hallucination_correction_prompt(
        invalid_ids={"E99"},
        available_ids={"E1"},
    )
    assert "do NOT exist" in prompt or "NOT exist" in prompt
