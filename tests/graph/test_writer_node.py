"""Tests for writer node.

These tests verify that:
1. Writer node returns correct state updates
2. Fallback behavior works correctly
3. LLM responses are parsed correctly
4. Citation validation works
5. Confidence calculation is applied
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.check_it_ai.graph.nodes.writer import writer_node
from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.types.evidence import EvidenceBundle, EvidenceItem, EvidenceVerdict

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
                title="Source 1 - Wikipedia",
                snippet="World War II ended in 1945.",
                url="https://en.wikipedia.org/wiki/WWII",
            ),
            EvidenceItem(
                id="E2",
                title="Source 2 - History.com",
                snippet="The war concluded on September 2, 1945.",
                url="https://www.history.com/wwii",
            ),
            EvidenceItem(
                id="E3",
                title="Source 3 - Britannica",
                snippet="V-J Day marked the end of World War II.",
                url="https://www.britannica.com/wwii",
            ),
        ],
        overall_verdict=EvidenceVerdict.SUPPORTED,
    )


@pytest.fixture
def state_with_evidence(sample_evidence_bundle: EvidenceBundle) -> AgentState:
    """Create an AgentState with evidence bundle populated."""
    return AgentState(
        user_query="When did World War II end?",
        evidence_bundle=sample_evidence_bundle,
        run_metadata={},
    )


@pytest.fixture
def state_without_evidence() -> AgentState:
    """Create an AgentState without evidence bundle."""
    return AgentState(
        user_query="When did World War II end?",
        evidence_bundle=None,
        run_metadata={},
    )


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response with valid JSON."""
    return json.dumps(
        {
            "answer": "World War II ended on September 2, 1945 [E1][E2].",
            "confidence": 0.9,
            "evidence_ids": ["E1", "E2"],
            "limitations": "Based on Western sources.",
        }
    )


# =============================================================================
# Test No Evidence Fallback
# =============================================================================


class TestNoEvidenceFallback:
    """Tests for no-evidence fallback behavior."""

    def test_returns_fallback_when_no_evidence_bundle(self, state_without_evidence: AgentState):
        """Should return fallback when evidence_bundle is None."""
        result = writer_node(state_without_evidence)

        assert "writer_output" in result
        assert result["writer_output"].fallback_used is True
        assert result["confidence"] == 0.2
        assert "cannot verify" in result["final_answer"].lower()

    def test_returns_fallback_when_empty_evidence_items(self):
        """Should return fallback when evidence_items is empty."""
        state = AgentState(
            user_query="Test query",
            evidence_bundle=EvidenceBundle(evidence_items=[]),
            run_metadata={},
        )

        result = writer_node(state)

        assert result["writer_output"].fallback_used is True
        assert result["run_metadata"]["writer"]["strategy"] == "no_evidence_fallback"

    def test_no_llm_call_when_no_evidence(self, state_without_evidence: AgentState):
        """Should not call LLM when there's no evidence."""
        mock_llm = MagicMock()

        result = writer_node(state_without_evidence, llm=mock_llm)

        mock_llm.invoke.assert_not_called()
        assert result["writer_output"].fallback_used is True


# =============================================================================
# Test LLM Error Fallback
# =============================================================================


class TestLLMErrorFallback:
    """Tests for LLM error fallback behavior."""

    def test_returns_fallback_on_llm_error(self, state_with_evidence: AgentState):
        """Should return fallback when LLM raises an exception."""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API Error")

        result = writer_node(state_with_evidence, llm=mock_llm)

        assert result["writer_output"].fallback_used is True
        assert "unavailable" in result["final_answer"].lower()
        assert result["run_metadata"]["writer"]["strategy"] == "generation_error_fallback"
        assert "API Error" in result["run_metadata"]["writer"]["error"]


# =============================================================================
# Test Successful LLM Response
# =============================================================================


class TestSuccessfulLLMResponse:
    """Tests for successful LLM response processing."""

    def test_returns_state_updates_dict(
        self,
        state_with_evidence: AgentState,
        mock_llm_response: str,
    ):
        """Should return a dict with state updates."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = mock_llm_response
        mock_llm.invoke.return_value = mock_response

        result = writer_node(state_with_evidence, llm=mock_llm)

        assert isinstance(result, dict)
        assert "writer_output" in result
        assert "final_answer" in result
        assert "confidence" in result
        assert "citations" in result
        assert "run_metadata" in result

    def test_parses_answer_from_llm_response(
        self,
        state_with_evidence: AgentState,
        mock_llm_response: str,
    ):
        """Should parse answer from LLM JSON response."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = mock_llm_response
        mock_llm.invoke.return_value = mock_response

        result = writer_node(state_with_evidence, llm=mock_llm)

        assert "World War II ended" in result["final_answer"]
        assert "[E1]" in result["final_answer"] or "E1" in result["writer_output"].evidence_ids

    def test_builds_citations_for_valid_evidence_ids(
        self,
        state_with_evidence: AgentState,
        mock_llm_response: str,
    ):
        """Should build Citation objects for valid evidence IDs."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = mock_llm_response
        mock_llm.invoke.return_value = mock_response

        result = writer_node(state_with_evidence, llm=mock_llm)

        assert len(result["citations"]) > 0
        assert all(c.evidence_id in ["E1", "E2", "E3"] for c in result["citations"])

    def test_applies_hybrid_confidence_calculation(
        self,
        state_with_evidence: AgentState,
    ):
        """Should apply hybrid confidence calculation."""
        # LLM returns high confidence
        llm_response = json.dumps(
            {
                "answer": "Answer with citations [E1][E2][E3].",
                "confidence": 0.95,
                "evidence_ids": ["E1", "E2", "E3"],
                "limitations": "",
            }
        )
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = llm_response
        mock_llm.invoke.return_value = mock_response

        result = writer_node(state_with_evidence, llm=mock_llm)

        # Confidence should be high but calculated via hybrid approach
        assert 0.7 <= result["confidence"] <= 1.0

    def test_records_latency_in_metadata(
        self,
        state_with_evidence: AgentState,
        mock_llm_response: str,
    ):
        """Should record latency in run_metadata."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = mock_llm_response
        mock_llm.invoke.return_value = mock_response

        result = writer_node(state_with_evidence, llm=mock_llm)

        assert "latency_seconds" in result["run_metadata"]["writer"]
        assert result["run_metadata"]["writer"]["latency_seconds"] >= 0


# =============================================================================
# Test Citation Validation
# =============================================================================


class TestCitationValidation:
    """Tests for citation validation behavior."""

    def test_valid_citations_pass_validation(self, state_with_evidence: AgentState):
        """Should mark citations as valid when all IDs exist in bundle."""
        llm_response = json.dumps(
            {
                "answer": "Answer with valid citations [E1][E2].",
                "confidence": 0.9,
                "evidence_ids": ["E1", "E2"],
                "limitations": "",
            }
        )
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = llm_response
        mock_llm.invoke.return_value = mock_response

        result = writer_node(state_with_evidence, llm=mock_llm)

        assert result["writer_output"].citation_valid is True
        assert result["run_metadata"]["writer"]["citation_valid"] is True

    def test_invalid_citations_trigger_fallback(self, state_with_evidence: AgentState):
        """Should trigger fallback when citations are invalid (hallucinated IDs)."""
        llm_response = json.dumps(
            {
                "answer": "Answer with hallucinated citation [E99].",
                "confidence": 0.9,
                "evidence_ids": ["E99"],
                "limitations": "",
            }
        )
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = llm_response
        mock_llm.invoke.return_value = mock_response

        result = writer_node(state_with_evidence, llm=mock_llm)

        assert result["writer_output"].citation_valid is False
        assert result["writer_output"].fallback_used is True
        assert "cannot safely verify" in result["final_answer"].lower()

    def test_no_citations_marks_invalid(self, state_with_evidence: AgentState):
        """Should mark as invalid when no citations are present."""
        llm_response = json.dumps(
            {
                "answer": "Answer without any citations.",
                "confidence": 0.9,
                "evidence_ids": [],
                "limitations": "",
            }
        )
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = llm_response
        mock_llm.invoke.return_value = mock_response

        result = writer_node(state_with_evidence, llm=mock_llm)

        assert result["writer_output"].citation_valid is False


# =============================================================================
# Test LLM Message Building
# =============================================================================


class TestLLMMessageBuilding:
    """Tests for LLM message construction."""

    def test_builds_messages_with_system_prompt(self, state_with_evidence: AgentState):
        """Should build messages starting with system prompt."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {"answer": "Test [E1].", "confidence": 0.9, "evidence_ids": ["E1"]}
        )
        mock_llm.invoke.return_value = mock_response

        writer_node(state_with_evidence, llm=mock_llm)

        # Check that invoke was called with a list of messages
        call_args = mock_llm.invoke.call_args[0][0]
        assert len(call_args) > 0
        # First message should be SystemMessage
        assert call_args[0].__class__.__name__ == "SystemMessage"

    def test_includes_few_shot_examples(self, state_with_evidence: AgentState):
        """Should include few-shot examples in messages."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {"answer": "Test [E1].", "confidence": 0.9, "evidence_ids": ["E1"]}
        )
        mock_llm.invoke.return_value = mock_response

        writer_node(state_with_evidence, llm=mock_llm)

        call_args = mock_llm.invoke.call_args[0][0]
        # Should have system + few-shot pairs + user = at least 8 messages
        # (1 system + 3 few-shot examples * 2 + 1 user = 8)
        assert len(call_args) >= 8


# =============================================================================
# Test Default LLM Creation
# =============================================================================


class TestDefaultLLMCreation:
    """Tests for default LLM creation when none provided."""

    @patch("src.check_it_ai.graph.nodes.writer.get_writer_llm")
    def test_creates_llm_from_settings_when_none_provided(
        self,
        mock_get_writer_llm: MagicMock,
        state_with_evidence: AgentState,
    ):
        """Should create LLM from settings when llm parameter is None."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {"answer": "Test [E1].", "confidence": 0.9, "evidence_ids": ["E1"]}
        )
        mock_llm.invoke.return_value = mock_response
        mock_get_writer_llm.return_value = mock_llm

        writer_node(state_with_evidence, llm=None)

        mock_get_writer_llm.assert_called_once()
