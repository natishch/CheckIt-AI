"""Integration tests for Fact Analyst → Writer node flow.

Tests the connection between Fact Analyst and Writer nodes with mocked LLMs.
Ensures that analyst output (evidence_bundle with findings) flows correctly
to the writer node.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import HttpUrl

from src.check_it_ai.graph.nodes.fact_analyst import fact_analyst_node
from src.check_it_ai.graph.nodes.writer import writer_node
from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.types.analyst import SingleEvaluation
from src.check_it_ai.types.evidence import EvidenceBundle, EvidenceVerdict
from src.check_it_ai.types.search import SearchResult


class TestAnalystWriterIntegration:
    """Test the Fact Analyst → Writer node integration."""

    @pytest.fixture
    def mock_search_results(self) -> list[SearchResult]:
        """Create mock search results for testing."""
        return [
            SearchResult(
                title="World War II - Wikipedia",
                snippet="World War II ended on September 2, 1945.",
                url=HttpUrl("https://en.wikipedia.org/wiki/World_War_II"),
                display_domain="en.wikipedia.org",
                rank=1,
            ),
            SearchResult(
                title="WW2 History - Britannica",
                snippet="The war concluded with Japan's surrender in 1945.",
                url=HttpUrl("https://britannica.com/wwii"),
                display_domain="britannica.com",
                rank=2,
            ),
        ]

    @pytest.fixture
    def mock_writer_response(self) -> str:
        """Create mock writer LLM response."""
        return json.dumps(
            {
                "answer": "World War II ended on September 2, 1945, with Japan's formal surrender [E1][E2].",
                "confidence": 0.9,
                "evidence_ids": ["E1", "E2"],
                "limitations": "",
            }
        )

    @patch("src.check_it_ai.graph.nodes.fact_analyst.evaluate_single_pair")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.extract_claims")
    def test_analyst_output_flows_to_writer(
        self,
        mock_extract_claims,
        mock_evaluate,
        mock_search_results,
        mock_writer_response,
    ):
        """Test that analyst output is properly consumed by writer node."""
        # Mock claim extraction
        mock_extract_claims.return_value = ["World War II ended in 1945"]

        # Mock evaluation to return SUPPORTED
        mock_evaluate.return_value = SingleEvaluation(
            verdict="SUPPORTED", confidence=0.9, reasoning="Evidence confirms WWII ended in 1945."
        )

        # Step 1: Run analyst node
        initial_state = AgentState(
            user_query="When did World War II end?",
            search_results=mock_search_results,
        )
        analyst_delta = fact_analyst_node(initial_state)

        # Verify analyst output
        bundle = analyst_delta["evidence_bundle"]
        assert bundle.overall_verdict == EvidenceVerdict.SUPPORTED
        assert len(bundle.findings) == 1
        assert len(bundle.items) == 2

        # Step 2: Update state with analyst output (simulating LangGraph merge)
        updated_state = AgentState(
            user_query=initial_state.user_query,
            search_results=initial_state.search_results,
            evidence_bundle=bundle,
            run_metadata=analyst_delta["run_metadata"],
        )

        # Step 3: Run writer node with mock LLM
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = mock_writer_response
        mock_llm.invoke.return_value = mock_response

        writer_delta = writer_node(updated_state, llm=mock_llm)

        # Verify writer consumed evidence bundle
        assert "final_answer" in writer_delta
        assert "World War II" in writer_delta["final_answer"]
        assert "[E1]" in writer_delta["final_answer"] or "E1" in str(writer_delta["citations"])

        # Verify writer recognized verdict
        assert writer_delta["writer_output"].verdict == EvidenceVerdict.SUPPORTED

    @patch("src.check_it_ai.graph.nodes.fact_analyst.evaluate_single_pair")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.extract_claims")
    def test_contested_verdict_flows_through(
        self,
        mock_extract_claims,
        mock_evaluate,
        mock_search_results,
    ):
        """Test that CONTESTED verdict from analyst flows to writer."""
        mock_extract_claims.return_value = ["The claim is true"]

        # Mock conflicting evaluations
        mock_evaluate.side_effect = [
            SingleEvaluation(verdict="SUPPORTED", confidence=0.8, reasoning="..."),
            SingleEvaluation(verdict="NOT_SUPPORTED", confidence=0.7, reasoning="..."),
        ]

        # Run analyst
        initial_state = AgentState(
            user_query="Is this claim true?",
            search_results=mock_search_results,
        )
        analyst_delta = fact_analyst_node(initial_state)

        # Verify contested verdict
        bundle = analyst_delta["evidence_bundle"]
        assert bundle.overall_verdict == EvidenceVerdict.CONTESTED

        # Update state and run writer
        updated_state = AgentState(
            user_query=initial_state.user_query,
            search_results=initial_state.search_results,
            evidence_bundle=bundle,
            run_metadata=analyst_delta["run_metadata"],
        )

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "answer": "The evidence is conflicting [E1][E2].",
                "confidence": 0.5,
                "evidence_ids": ["E1", "E2"],
            }
        )
        mock_llm.invoke.return_value = mock_response

        writer_delta = writer_node(updated_state, llm=mock_llm)

        # Writer should recognize contested verdict
        assert writer_delta["writer_output"].verdict == EvidenceVerdict.CONTESTED

    @patch("src.check_it_ai.graph.nodes.fact_analyst.evaluate_single_pair")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.extract_claims")
    def test_findings_populated_in_bundle(
        self,
        mock_extract_claims,
        mock_evaluate,
        mock_search_results,
    ):
        """Test that findings are properly populated and accessible."""
        mock_extract_claims.return_value = [
            "Einstein invented the light bulb",
            "Einstein won a Nobel Prize",
        ]

        # First claim NOT_SUPPORTED, second SUPPORTED
        mock_evaluate.side_effect = [
            # First claim against both evidence items
            SingleEvaluation(
                verdict="NOT_SUPPORTED", confidence=0.85, reasoning="Edison invented it"
            ),
            SingleEvaluation(verdict="NOT_SUPPORTED", confidence=0.80, reasoning="Edison did"),
            # Second claim against both evidence items
            SingleEvaluation(verdict="SUPPORTED", confidence=0.9, reasoning="Nobel 1921"),
            SingleEvaluation(verdict="SUPPORTED", confidence=0.85, reasoning="Physics prize"),
        ]

        initial_state = AgentState(
            user_query="Einstein invented the light bulb and won a Nobel Prize",
            search_results=mock_search_results,
        )
        analyst_delta = fact_analyst_node(initial_state)

        bundle = analyst_delta["evidence_bundle"]

        # Verify findings structure
        assert len(bundle.findings) == 2
        assert bundle.findings[0].claim == "Einstein invented the light bulb"
        assert bundle.findings[0].verdict == EvidenceVerdict.NOT_SUPPORTED
        assert bundle.findings[1].claim == "Einstein won a Nobel Prize"
        assert bundle.findings[1].verdict == EvidenceVerdict.SUPPORTED

        # Overall should be NOT_SUPPORTED (priority over SUPPORTED)
        assert bundle.overall_verdict == EvidenceVerdict.NOT_SUPPORTED

    @patch("src.check_it_ai.graph.nodes.fact_analyst.evaluate_single_pair")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.extract_claims")
    def test_metadata_preserved_through_pipeline(
        self,
        mock_extract_claims,
        mock_evaluate,
        mock_search_results,
        mock_writer_response,
    ):
        """Test that metadata is preserved and accumulated through the pipeline."""
        mock_extract_claims.return_value = ["Test claim"]
        mock_evaluate.return_value = SingleEvaluation(
            verdict="SUPPORTED", confidence=0.9, reasoning="..."
        )

        # Initial state with router metadata
        initial_state = AgentState(
            user_query="Test query",
            search_results=mock_search_results,
            run_metadata={"router": {"decision": "fact_check", "confidence": 0.85}},
        )

        # Run analyst
        analyst_delta = fact_analyst_node(initial_state)

        # Check analyst added its metadata
        assert "fact_analyst" in analyst_delta["run_metadata"]
        assert "claims_extracted" in analyst_delta["run_metadata"]["fact_analyst"]

        # Update state with analyst output
        updated_state = AgentState(
            user_query=initial_state.user_query,
            search_results=initial_state.search_results,
            evidence_bundle=analyst_delta["evidence_bundle"],
            run_metadata=analyst_delta["run_metadata"],
        )

        # Run writer
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = mock_writer_response
        mock_llm.invoke.return_value = mock_response

        writer_delta = writer_node(updated_state, llm=mock_llm)

        # Verify all metadata is preserved
        final_metadata = writer_delta["run_metadata"]
        assert "router" in final_metadata  # From initial state
        assert "fact_analyst" in final_metadata  # From analyst
        assert "writer" in final_metadata  # From writer

    def test_empty_evidence_skips_writer_llm(self):
        """Test that writer uses fallback when no evidence from analyst."""
        # Simulate analyst returning empty results
        bundle = EvidenceBundle(
            items=[],
            findings=[],
            overall_verdict=EvidenceVerdict.INSUFFICIENT,
        )

        state = AgentState(
            user_query="Test query",
            evidence_bundle=bundle,
        )

        # Writer should not call LLM
        mock_llm = MagicMock()
        writer_delta = writer_node(state, llm=mock_llm)

        # LLM should not be called
        mock_llm.invoke.assert_not_called()

        # Should use fallback
        assert writer_delta["writer_output"].fallback_used is True
        assert "cannot verify" in writer_delta["final_answer"].lower()


class TestEndToEndStateFlow:
    """Test complete state flow from search results through analyst to writer."""

    @pytest.fixture
    def full_pipeline_search_results(self) -> list[SearchResult]:
        """Create search results for full pipeline test."""
        return [
            SearchResult(
                title="NASA Moon Landing",
                snippet="Apollo 11 landed on the Moon on July 20, 1969.",
                url=HttpUrl("https://nasa.gov/apollo11"),
                display_domain="nasa.gov",
                rank=1,
            ),
            SearchResult(
                title="Moon Landing History",
                snippet="Neil Armstrong was the first human to walk on the Moon in 1969.",
                url=HttpUrl("https://history.com/moon"),
                display_domain="history.com",
                rank=2,
            ),
        ]

    @patch("src.check_it_ai.graph.nodes.fact_analyst.evaluate_single_pair")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.extract_claims")
    def test_full_pipeline_state_consistency(
        self,
        mock_extract_claims,
        mock_evaluate,
        full_pipeline_search_results,
    ):
        """Test that state remains consistent through the entire pipeline."""
        mock_extract_claims.return_value = ["The Moon landing occurred in 1969"]
        mock_evaluate.return_value = SingleEvaluation(
            verdict="SUPPORTED", confidence=0.95, reasoning="NASA confirms 1969 landing"
        )

        user_query = "Did humans land on the Moon in 1969?"

        # Step 1: Initialize state (simulating post-researcher)
        state = AgentState(
            user_query=user_query,
            search_results=full_pipeline_search_results,
            run_metadata={"researcher": {"query_count": 3}},
        )

        # Step 2: Analyst node
        analyst_delta = fact_analyst_node(state)

        # Verify analyst output
        assert analyst_delta["evidence_bundle"] is not None
        assert analyst_delta["evidence_bundle"].overall_verdict == EvidenceVerdict.SUPPORTED

        # Step 3: Merge state (simulating LangGraph)
        state.evidence_bundle = analyst_delta["evidence_bundle"]
        state.run_metadata = analyst_delta["run_metadata"]

        # Step 4: Writer node
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "answer": "Yes, humans landed on the Moon in 1969 [E1][E2].",
                "confidence": 0.95,
                "evidence_ids": ["E1", "E2"],
            }
        )
        mock_llm.invoke.return_value = mock_response

        writer_delta = writer_node(state, llm=mock_llm)

        # Verify final output
        assert "Moon" in writer_delta["final_answer"] or "1969" in writer_delta["final_answer"]
        assert writer_delta["writer_output"].verdict == EvidenceVerdict.SUPPORTED
        assert len(writer_delta["citations"]) >= 1

        # Verify metadata chain
        final_metadata = writer_delta["run_metadata"]
        assert "researcher" in final_metadata
        assert "fact_analyst" in final_metadata
        assert "writer" in final_metadata
