"""Integration tests for Router → Researcher node flow.

Tests the connection between Router and Researcher nodes with mocked APIs.
"""

from unittest.mock import patch

import pytest

from check_it_ai.graph.nodes.researcher import researcher_node
from check_it_ai.graph.nodes.router import router_node
from check_it_ai.graph.state import AgentState
from check_it_ai.types.schemas import RouterDecision, RouterTrigger, SearchResult


class TestRouterResearcherIntegration:
    """Test the Router → Researcher node integration."""

    @pytest.fixture
    def mock_search_results(self) -> list[SearchResult]:
        """Create mock search results for testing."""
        return [
            SearchResult(
                title="World War II - Wikipedia",
                snippet="World War II ended in 1945...",
                url="https://en.wikipedia.org/wiki/World_War_II",
                display_domain="en.wikipedia.org",
                rank=1,
            ),
            SearchResult(
                title="WW2 Facts",
                snippet="Key facts about World War II",
                url="https://www.history.com/topics/world-war-ii",
                display_domain="history.com",
                rank=2,
            ),
        ]

    @patch("check_it_ai.graph.nodes.researcher.google_search")
    def test_fact_check_route_triggers_researcher(self, mock_google_search, mock_search_results):
        """Test that router decision 'fact_check' successfully triggers researcher node."""
        # Mock Google Search API
        mock_google_search.return_value = mock_search_results

        # Step 1: Router classifies query
        initial_state = AgentState(user_query="When did World War II end?")
        router_state = router_node(initial_state)

        # Verify router routed to fact_check
        assert router_state.route == RouterDecision.FACT_CHECK
        assert router_state.run_metadata["router"]["decision"] == RouterDecision.FACT_CHECK

        # Step 2: Researcher node executes (receives full state from router)
        researcher_delta = researcher_node(router_state)

        # Verify researcher executed successfully
        assert len(researcher_delta["search_queries"]) > 0
        assert len(researcher_delta["search_results"]) > 0

        # Verify search was executed (3 queries for query expansion)
        assert mock_google_search.call_count == 3

    @patch("check_it_ai.graph.nodes.researcher.google_search")
    def test_clarify_route_skips_researcher(self, mock_google_search):
        """Test that router decision 'clarify' does not trigger researcher."""
        # Router classifies empty query
        initial_state = AgentState(user_query="")
        router_state = router_node(initial_state)

        # Verify router routed to clarify
        assert router_state.route == RouterDecision.CLARIFY

        # In real graph, clarify route would skip researcher
        # (Simulating conditional edge logic)
        should_run_researcher = router_state.route == RouterDecision.FACT_CHECK
        assert should_run_researcher is False

        # Verify google_search was never called
        mock_google_search.assert_not_called()

    @patch("check_it_ai.graph.nodes.researcher.google_search")
    def test_out_of_scope_route_skips_researcher(self, mock_google_search):
        """Test that router decision 'out_of_scope' does not trigger researcher."""
        # Router classifies coding request
        initial_state = AgentState(user_query="Write a Python script to sort a list")
        router_state = router_node(initial_state)

        # Verify router routed to out_of_scope
        assert router_state.route == RouterDecision.OUT_OF_SCOPE

        # In real graph, out_of_scope route would terminate
        should_run_researcher = router_state.route == RouterDecision.FACT_CHECK
        assert should_run_researcher is False

        # Verify google_search was never called
        mock_google_search.assert_not_called()

    @patch("check_it_ai.graph.nodes.researcher.google_search")
    def test_end_to_end_state_flow(self, mock_google_search, mock_search_results):
        """Test complete state flow from user query through router to researcher."""
        mock_google_search.return_value = mock_search_results

        # Initial user query
        user_query = "Is it true that Napoleon Bonaparte died in 1821?"

        # Step 1: Start with empty state
        state = AgentState(user_query=user_query)

        # Step 2: Router node (returns full AgentState)
        router_state = router_node(state)

        # Verify router state
        assert router_state.route == RouterDecision.FACT_CHECK
        assert router_state.user_query == user_query
        assert "router" in router_state.run_metadata

        # Step 3: Researcher node (only if fact_check)
        if router_state.route == RouterDecision.FACT_CHECK:
            researcher_delta = researcher_node(router_state)
            # Manually update state with researcher delta (simulating LangGraph merge)
            router_state.search_queries = researcher_delta["search_queries"]
            router_state.search_results = researcher_delta["search_results"]

        # Verify final state
        assert router_state.user_query == user_query
        assert router_state.route == RouterDecision.FACT_CHECK
        assert len(router_state.search_queries) == 3  # Query expansion
        assert len(router_state.search_results) > 0
        assert "router" in router_state.run_metadata

    @patch("check_it_ai.graph.nodes.researcher.google_search")
    def test_router_metadata_preserved_through_researcher(
        self, mock_google_search, mock_search_results
    ):
        """Test that router metadata is preserved when researcher executes."""
        mock_google_search.return_value = mock_search_results

        # Router execution (returns full AgentState)
        initial_state = AgentState(user_query="When was the Battle of Waterloo?")
        router_state = router_node(initial_state)

        router_metadata = router_state.run_metadata["router"]

        # Researcher execution
        researcher_delta = researcher_node(router_state)

        # Manually update state with researcher delta (simulating LangGraph merge)
        router_state.search_queries = researcher_delta["search_queries"]
        router_state.search_results = researcher_delta["search_results"]

        # Verify router metadata is still present
        assert "router" in router_state.run_metadata
        assert router_state.run_metadata["router"] == router_metadata
        assert router_state.run_metadata["router"]["trigger"] in [
            RouterTrigger.EXPLICIT_VERIFICATION,
            RouterTrigger.DEFAULT_FACT_CHECK,
        ]
        assert router_state.run_metadata["router"]["confidence"] > 0.0

    @patch("check_it_ai.graph.nodes.researcher.google_search")
    def test_query_expansion_based_on_router_classification(
        self, mock_google_search, mock_search_results
    ):
        """Test that researcher expands queries appropriately after router classification."""
        mock_google_search.return_value = mock_search_results

        # Verification question (will trigger explicit_verification)
        state = AgentState(user_query="Is it true that the Earth is round?")
        router_state = router_node(state)

        # Verify router detected verification pattern
        assert router_state.run_metadata["router"]["trigger"] == RouterTrigger.EXPLICIT_VERIFICATION
        # Confidence can vary based on query features - just verify it's positive
        assert router_state.run_metadata["router"]["confidence"] > 0.0

        # Run researcher
        researcher_delta = researcher_node(router_state)

        # Verify query expansion happened
        search_queries = researcher_delta["search_queries"]
        assert len(search_queries) >= 1
        assert len(search_queries) <= 3

        # Verify base query is present
        base_query = search_queries[0].query
        assert "Earth is round" in base_query or "the Earth is round" in base_query
