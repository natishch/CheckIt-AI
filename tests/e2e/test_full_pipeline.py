"""End-to-end tests for the full fact-checking pipeline.

Tests the complete flow: Router → Researcher → Analyst → Writer
with REAL API calls (Google Search + LLM).

Run with: uv run pytest tests/e2e/test_full_pipeline.py -v -s -m e2e
"""

import pytest

from src.check_it_ai.config import settings
from src.check_it_ai.graph.nodes.fact_analyst import fact_analyst_node
from src.check_it_ai.graph.nodes.researcher import researcher_node
from src.check_it_ai.graph.nodes.router import router_node
from src.check_it_ai.graph.nodes.writer import writer_node
from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.llm.providers import check_provider_health
from src.check_it_ai.types import RouterDecision


def _has_google_api() -> bool:
    """Check if Google API credentials are configured."""
    return bool(settings.google_api_key and settings.google_cse_id)


def _has_llm_available() -> bool:
    """Check if LLM is available."""
    health = check_provider_health(settings)
    return health.get("healthy", False)


@pytest.mark.e2e
class TestFullPipelineE2E:
    """End-to-end tests for complete Router → Researcher → Analyst → Writer flow."""

    @pytest.fixture(autouse=True)
    def check_apis(self):
        """Skip if required APIs are not configured."""
        if not _has_google_api():
            pytest.skip("Google API credentials not configured")
        if not _has_llm_available():
            pytest.skip("No LLM available (configure cloud API key or local LLM)")

    def test_full_pipeline_supported_claim(self):
        """E2E: Test full pipeline with a clearly supported historical claim."""
        user_query = "Did World War II end in 1945?"

        # Step 1: Router
        state = AgentState(user_query=user_query)
        router_state = router_node(state)

        assert router_state.route == RouterDecision.FACT_CHECK
        print(f"\n✓ Router: {router_state.run_metadata['router']['trigger']}")

        # Step 2: Researcher (real Google API)
        researcher_delta = researcher_node(router_state)

        assert len(researcher_delta["search_results"]) > 0
        print(f"✓ Researcher: {len(researcher_delta['search_results'])} results")

        # Step 3: Analyst (real LLM)
        analyst_state = AgentState(
            user_query=user_query,
            search_results=researcher_delta["search_results"],
            run_metadata=router_state.run_metadata,
        )
        analyst_delta = fact_analyst_node(analyst_state)

        bundle = analyst_delta["evidence_bundle"]
        assert bundle is not None
        assert len(bundle.findings) >= 1
        print(f"✓ Analyst: {bundle.overall_verdict.value} ({len(bundle.findings)} findings)")

        # Step 4: Writer (real LLM)
        writer_state = AgentState(
            user_query=user_query,
            search_results=researcher_delta["search_results"],
            evidence_bundle=bundle,
            run_metadata=analyst_delta["run_metadata"],
        )
        writer_delta = writer_node(writer_state)

        assert "final_answer" in writer_delta
        assert len(writer_delta["final_answer"]) > 50  # Non-trivial answer
        print(f"✓ Writer: Generated answer ({len(writer_delta['final_answer'])} chars)")
        print(f"\nFinal Answer:\n{writer_delta['final_answer'][:500]}...")

        # Verify metadata chain
        metadata = writer_delta["run_metadata"]
        assert "router" in metadata
        assert "fact_analyst" in metadata
        assert "writer" in metadata

    def test_full_pipeline_refuted_claim(self):
        """E2E: Test full pipeline with a clearly false claim."""
        user_query = "Did Einstein invent the telephone?"

        # Step 1: Router
        state = AgentState(user_query=user_query)
        router_state = router_node(state)

        assert router_state.route == RouterDecision.FACT_CHECK
        print(f"\n✓ Router: {router_state.run_metadata['router']['trigger']}")

        # Step 2: Researcher
        researcher_delta = researcher_node(router_state)
        print(f"✓ Researcher: {len(researcher_delta['search_results'])} results")

        # Step 3: Analyst
        analyst_state = AgentState(
            user_query=user_query,
            search_results=researcher_delta["search_results"],
            run_metadata=router_state.run_metadata,
        )
        analyst_delta = fact_analyst_node(analyst_state)

        bundle = analyst_delta["evidence_bundle"]
        print(f"✓ Analyst: {bundle.overall_verdict.value}")

        # Step 4: Writer
        writer_state = AgentState(
            user_query=user_query,
            search_results=researcher_delta["search_results"],
            evidence_bundle=bundle,
            run_metadata=analyst_delta["run_metadata"],
        )
        writer_delta = writer_node(writer_state)

        print("✓ Writer: Generated answer")
        print(f"\nFinal Answer:\n{writer_delta['final_answer'][:500]}...")

        # The answer should mention the claim is incorrect
        answer_lower = writer_delta["final_answer"].lower()
        assert any(
            word in answer_lower
            for word in [
                "not",
                "false",
                "incorrect",
                "wrong",
                "did not",
                "didn't",
                "bell",
                "graham",
                "alexander",  # Bell invented telephone
            ]
        )

    def test_full_pipeline_out_of_scope_skips_research(self):
        """E2E: Test that out-of-scope queries don't trigger research."""
        user_query = "Write a Python function to sort a list"

        # Router should classify as out_of_scope
        state = AgentState(user_query=user_query)
        router_state = router_node(state)

        assert router_state.route == RouterDecision.OUT_OF_SCOPE
        print("\n✓ Router: Correctly identified out-of-scope query")

        # In real graph, this would END without calling researcher
        should_continue = router_state.route == RouterDecision.FACT_CHECK
        assert not should_continue
        print("✓ Pipeline: Correctly terminated (no API calls made)")

    def test_full_pipeline_clarify_skips_research(self):
        """E2E: Test that ambiguous queries request clarification."""
        user_query = "Is it true?"  # Too vague

        # Router should request clarification
        state = AgentState(user_query=user_query)
        router_state = router_node(state)

        assert router_state.route == RouterDecision.CLARIFY
        print("\n✓ Router: Correctly requested clarification")

        # In real graph, this would END without calling researcher
        should_continue = router_state.route == RouterDecision.FACT_CHECK
        assert not should_continue
        print("✓ Pipeline: Correctly terminated (no API calls made)")

    def test_full_pipeline_metadata_complete(self):
        """E2E: Verify all pipeline stages populate metadata."""
        user_query = "When did the Berlin Wall fall?"

        # Run full pipeline
        state = AgentState(user_query=user_query)
        router_state = router_node(state)
        researcher_delta = researcher_node(router_state)

        analyst_state = AgentState(
            user_query=user_query,
            search_results=researcher_delta["search_results"],
            run_metadata=router_state.run_metadata,
        )
        analyst_delta = fact_analyst_node(analyst_state)

        writer_state = AgentState(
            user_query=user_query,
            search_results=researcher_delta["search_results"],
            evidence_bundle=analyst_delta["evidence_bundle"],
            run_metadata=analyst_delta["run_metadata"],
        )
        writer_delta = writer_node(writer_state)

        # Verify complete metadata
        metadata = writer_delta["run_metadata"]

        # Router metadata
        assert "router" in metadata
        assert "trigger" in metadata["router"]
        assert "decision" in metadata["router"]
        assert "confidence" in metadata["router"]
        print(f"\n✓ Router metadata: {metadata['router']['decision']}")

        # Analyst metadata
        assert "fact_analyst" in metadata
        assert "claims_extracted" in metadata["fact_analyst"]
        assert "overall_verdict" in metadata["fact_analyst"]
        print(f"✓ Analyst metadata: {metadata['fact_analyst']['overall_verdict']}")

        # Writer metadata
        assert "writer" in metadata
        assert "strategy" in metadata["writer"]
        assert "latency_seconds" in metadata["writer"]
        print(f"✓ Writer metadata: strategy={metadata['writer']['strategy']}")


@pytest.mark.e2e
class TestPipelineWithVariousQueries:
    """Test pipeline with various query types."""

    @pytest.fixture(autouse=True)
    def check_apis(self):
        """Skip if required APIs are not configured."""
        if not _has_google_api():
            pytest.skip("Google API credentials not configured")
        if not _has_llm_available():
            pytest.skip("No LLM available")

    @pytest.mark.parametrize(
        "query,expected_route",
        [
            ("When did World War I start?", RouterDecision.FACT_CHECK),
            ("Is it true that Napoleon was short?", RouterDecision.FACT_CHECK),
            ("Write me a poem about history", RouterDecision.OUT_OF_SCOPE),
            ("Tell me a joke about Caesar", RouterDecision.OUT_OF_SCOPE),
            ("", RouterDecision.CLARIFY),
            ("is it true?", RouterDecision.CLARIFY),  # Underspecified verification question
        ],
    )
    def test_router_classification(self, query, expected_route):
        """Parametrized test for router classification."""
        state = AgentState(user_query=query)
        router_state = router_node(state)

        assert router_state.route == expected_route, (
            f"Query '{query}' expected {expected_route}, got {router_state.route}"
        )
