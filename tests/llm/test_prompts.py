"""Tests for LLM prompts module.

These tests verify that:
1. Evidence is properly formatted for LLM prompts
2. Few-shot examples are correctly structured
3. User prompts are built correctly
"""

import pytest

from src.check_it_ai.llm.prompts import (
    FEW_SHOT_EXAMPLES,
    SYSTEM_PROMPT,
    build_few_shot_messages,
    build_user_prompt,
    format_evidence_for_prompt,
)
from src.check_it_ai.types.evidence import EvidenceBundle, EvidenceItem, EvidenceVerdict

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_evidence_item() -> EvidenceItem:
    """Create a sample evidence item."""
    return EvidenceItem(
        id="E1",
        title="Test Source - Wikipedia",
        snippet="This is a test snippet with important information.",
        url="https://en.wikipedia.org/wiki/Test",
    )


@pytest.fixture
def sample_evidence_bundle(sample_evidence_item: EvidenceItem) -> EvidenceBundle:
    """Create a sample evidence bundle with multiple items."""
    return EvidenceBundle(
        evidence_items=[
            sample_evidence_item,
            EvidenceItem(
                id="E2",
                title="Another Source - History.com",
                snippet="Additional test content for verification.",
                url="https://www.history.com/test",
            ),
        ],
        overall_verdict=EvidenceVerdict.SUPPORTED,
    )


# =============================================================================
# Test System Prompt
# =============================================================================


def test_system_prompt_exists():
    """System prompt should be non-empty."""
    assert SYSTEM_PROMPT
    assert len(SYSTEM_PROMPT) > 100  # Should be substantial


def test_system_prompt_contains_key_instructions():
    """System prompt should contain key instructions for the historian persona."""
    # Core principles
    assert "Evidence-Only Answers" in SYSTEM_PROMPT
    assert "Mandatory Citations" in SYSTEM_PROMPT
    assert "Neutral Tone" in SYSTEM_PROMPT

    # Output format
    assert "JSON" in SYSTEM_PROMPT
    assert "answer" in SYSTEM_PROMPT
    assert "confidence" in SYSTEM_PROMPT
    assert "evidence_ids" in SYSTEM_PROMPT
    assert "limitations" in SYSTEM_PROMPT

    # Confidence guidelines
    assert "0.9-1.0" in SYSTEM_PROMPT
    assert "0.0-0.29" in SYSTEM_PROMPT


def test_system_prompt_mentions_citation_format():
    """System prompt should specify the citation format [E1], [E2], etc."""
    assert "[E1]" in SYSTEM_PROMPT
    assert "[E2]" in SYSTEM_PROMPT


# =============================================================================
# Test Few-Shot Examples
# =============================================================================


def test_few_shot_examples_count():
    """Should have exactly 3 few-shot examples."""
    assert len(FEW_SHOT_EXAMPLES) == 3


def test_few_shot_examples_structure():
    """Each example should have input and output fields."""
    for i, example in enumerate(FEW_SHOT_EXAMPLES):
        assert "input" in example, f"Example {i} missing 'input'"
        assert "output" in example, f"Example {i} missing 'output'"
        assert len(example["input"]) > 0, f"Example {i} has empty input"
        assert len(example["output"]) > 0, f"Example {i} has empty output"


def test_few_shot_examples_contain_evidence():
    """Each example input should contain evidence markers."""
    for i, example in enumerate(FEW_SHOT_EXAMPLES):
        assert "[E1]" in example["input"], f"Example {i} input missing [E1]"
        assert "Question:" in example["input"], f"Example {i} input missing Question:"


def test_few_shot_examples_output_is_json():
    """Each example output should be valid JSON-like structure."""
    import json

    for i, example in enumerate(FEW_SHOT_EXAMPLES):
        try:
            data = json.loads(example["output"])
            assert "answer" in data, f"Example {i} output missing 'answer'"
            assert "confidence" in data, f"Example {i} output missing 'confidence'"
            assert "evidence_ids" in data, f"Example {i} output missing 'evidence_ids'"
        except json.JSONDecodeError:
            pytest.fail(f"Example {i} output is not valid JSON")


def test_few_shot_example_1_high_confidence():
    """First example should demonstrate high confidence (supported claim)."""
    import json

    data = json.loads(FEW_SHOT_EXAMPLES[0]["output"])
    assert data["confidence"] >= 0.9, "Example 1 should have high confidence"
    assert len(data["evidence_ids"]) >= 2, "Example 1 should use multiple sources"


def test_few_shot_example_2_medium_confidence():
    """Second example should demonstrate medium confidence (contested claim)."""
    import json

    data = json.loads(FEW_SHOT_EXAMPLES[1]["output"])
    assert 0.5 <= data["confidence"] <= 0.8, "Example 2 should have medium confidence"
    assert data["limitations"], "Example 2 should have limitations"


def test_few_shot_example_3_low_confidence():
    """Third example should demonstrate low confidence (insufficient evidence)."""
    import json

    data = json.loads(FEW_SHOT_EXAMPLES[2]["output"])
    assert data["confidence"] <= 0.3, "Example 3 should have low confidence"
    assert "cannot" in data["answer"].lower(), "Example 3 should decline to answer"


# =============================================================================
# Test Evidence Formatting
# =============================================================================


def test_format_evidence_empty_bundle():
    """Empty bundle should return 'No evidence available.'"""
    result = format_evidence_for_prompt(None)
    assert result == "No evidence available."

    result = format_evidence_for_prompt(EvidenceBundle(evidence_items=[]))
    assert result == "No evidence available."


def test_format_evidence_single_item(sample_evidence_item: EvidenceItem):
    """Single item should be formatted correctly."""
    bundle = EvidenceBundle(evidence_items=[sample_evidence_item])
    result = format_evidence_for_prompt(bundle)

    assert "[E1]" in result
    assert "Test Source - Wikipedia" in result
    assert "This is a test snippet" in result
    assert "https://en.wikipedia.org/wiki/Test" in result


def test_format_evidence_multiple_items(sample_evidence_bundle: EvidenceBundle):
    """Multiple items should all be included in output."""
    result = format_evidence_for_prompt(sample_evidence_bundle)

    assert "[E1]" in result
    assert "[E2]" in result
    assert "Test Source - Wikipedia" in result
    assert "Another Source - History.com" in result


def test_format_evidence_structure(sample_evidence_bundle: EvidenceBundle):
    """Output should have consistent structure with Title, Snippet, URL."""
    result = format_evidence_for_prompt(sample_evidence_bundle)

    assert "Title:" in result
    assert "Snippet:" in result
    assert "URL:" in result


def test_format_evidence_preserves_order(sample_evidence_bundle: EvidenceBundle):
    """Evidence items should be in same order as in bundle."""
    result = format_evidence_for_prompt(sample_evidence_bundle)

    e1_pos = result.find("[E1]")
    e2_pos = result.find("[E2]")

    assert e1_pos < e2_pos, "E1 should appear before E2"


# =============================================================================
# Test User Prompt Building
# =============================================================================


def test_build_user_prompt_includes_evidence(sample_evidence_bundle: EvidenceBundle):
    """User prompt should include formatted evidence."""
    query = "When did World War II end?"
    result = build_user_prompt(query, sample_evidence_bundle)

    assert "Evidence:" in result
    assert "[E1]" in result
    assert "[E2]" in result


def test_build_user_prompt_includes_question(sample_evidence_bundle: EvidenceBundle):
    """User prompt should include the question."""
    query = "When did World War II end?"
    result = build_user_prompt(query, sample_evidence_bundle)

    assert "Question:" in result
    assert query in result


def test_build_user_prompt_no_evidence():
    """User prompt with no evidence should still work."""
    query = "Test question?"
    result = build_user_prompt(query, None)

    assert "Question:" in result
    assert query in result
    assert "No evidence available." in result


def test_build_user_prompt_question_at_end(sample_evidence_bundle: EvidenceBundle):
    """Question should appear after evidence in prompt."""
    query = "Test question?"
    result = build_user_prompt(query, sample_evidence_bundle)

    evidence_pos = result.find("Evidence:")
    question_pos = result.find("Question:")

    assert evidence_pos < question_pos, "Evidence should appear before Question"


# =============================================================================
# Test Few-Shot Message Building
# =============================================================================


def test_build_few_shot_messages_count():
    """Should generate 2 messages per example (user + assistant)."""
    messages = build_few_shot_messages()
    expected_count = len(FEW_SHOT_EXAMPLES) * 2
    assert len(messages) == expected_count


def test_build_few_shot_messages_structure():
    """Each message should have role and content."""
    messages = build_few_shot_messages()

    for msg in messages:
        assert "role" in msg
        assert "content" in msg
        assert msg["role"] in ("user", "assistant")


def test_build_few_shot_messages_alternating():
    """Messages should alternate user/assistant."""
    messages = build_few_shot_messages()

    for i, msg in enumerate(messages):
        expected_role = "user" if i % 2 == 0 else "assistant"
        assert msg["role"] == expected_role, f"Message {i} has wrong role"


def test_build_few_shot_messages_content_matches_examples():
    """Message content should match the example inputs/outputs."""
    messages = build_few_shot_messages()

    for i, example in enumerate(FEW_SHOT_EXAMPLES):
        user_msg = messages[i * 2]
        assistant_msg = messages[i * 2 + 1]

        assert user_msg["content"] == example["input"]
        assert assistant_msg["content"] == example["output"]
