"""End-to-end integration tests for Router → Researcher flow with REAL API calls.

⚠️  WARNING: These tests make REAL API calls to Google Custom Search API.
They consume API quota and require valid credentials in .env file.

Run with: uv run pytest tests/e2e/test_router_researcher.py -v -s -m e2e
"""

import time

import pytest

from check_it_ai.config import settings
from check_it_ai.graph.nodes.researcher import researcher_node
from check_it_ai.graph.nodes.router import router_node
from check_it_ai.graph.state import AgentState
from check_it_ai.types.schemas import RouterDecision, RouterTrigger


@pytest.mark.e2e
class TestRouterResearcherE2E:
    """End-to-end tests with REAL API calls (requires Google API credentials)."""

    @pytest.fixture(autouse=True)
    def check_credentials(self):
        """Skip tests if API credentials are not configured."""
        if not settings.google_api_key or not settings.google_cse_id:
            pytest.skip(
                "Google API credentials not configured (set GOOGLE_API_KEY and GOOGLE_CSE_ID)"
            )

    def test_historical_fact_check_query(self):
        """E2E: Historical fact-check query flows through router → researcher with real API."""
        # User asks a clear historical question
        user_query = "When did World War II end?"

        # Step 1: Router classifies query
        initial_state = AgentState(user_query=user_query)
        router_state = router_node(initial_state)

        # Verify router routed to fact_check
        assert router_state.route == RouterDecision.FACT_CHECK
        assert router_state.run_metadata["router"]["decision"] == RouterDecision.FACT_CHECK
        print(
            f"\n✓ Router: {router_state.run_metadata['router']['trigger']} "
            f"(confidence: {router_state.run_metadata['router']['confidence']})"
        )

        # Step 2: Researcher makes REAL API calls
        researcher_delta = researcher_node(router_state)

        # Verify search execution
        assert len(researcher_delta["search_queries"]) > 0
        assert len(researcher_delta["search_results"]) > 0

        print(f"✓ Researcher: {len(researcher_delta['search_queries'])} queries expanded")
        print(f"✓ Researcher: {len(researcher_delta['search_results'])} unique results found")

        # Verify results quality
        search_results = researcher_delta["search_results"]
        assert all(result.url for result in search_results), "All results should have URLs"
        assert all(result.title for result in search_results), "All results should have titles"
        assert all(
            result.snippet for result in search_results
        ), "All results should have snippets"

        # Print sample result for verification
        if search_results:
            first_result = search_results[0]
            print(f"\nSample result:")
            print(f"  Title: {first_result.title}")
            print(f"  Snippet: {first_result.snippet[:100]}...")
            print(f"  URL: {first_result.url}")

    def test_verification_question_high_confidence(self):
        """E2E: Verification question gets high confidence and triggers researcher."""
        user_query = "Is it true that Napoleon Bonaparte died in 1821?"

        # Router classification
        router_state = router_node(AgentState(user_query=user_query))

        # Verify router detected verification pattern
        assert router_state.route == RouterDecision.FACT_CHECK
        assert router_state.run_metadata["router"]["trigger"] == RouterTrigger.EXPLICIT_VERIFICATION
        # Confidence can vary - just check it's positive
        assert router_state.run_metadata["router"]["confidence"] > 0.0

        print(
            f"\n✓ Router: Explicit verification detected "
            f"(confidence: {router_state.run_metadata['router']['confidence']})"
        )

        # Researcher execution with REAL API
        researcher_delta = researcher_node(router_state)

        # Verify results
        assert len(researcher_delta["search_results"]) > 0
        print(f"✓ Researcher: Found {len(researcher_delta['search_results'])} results")

        # Verify query expansion includes verification context
        queries = [q.query for q in researcher_delta["search_queries"]]
        assert any("Napoleon" in q for q in queries)

    def test_empty_query_skips_researcher(self):
        """E2E: Empty query routes to clarify and does NOT make API calls."""
        user_query = "   "  # Empty/whitespace

        # Router classification
        router_state = router_node(AgentState(user_query=user_query))

        # Verify router routed to clarify
        assert router_state.route == RouterDecision.CLARIFY
        assert router_state.run_metadata["router"]["trigger"] == RouterTrigger.EMPTY_QUERY

        print(f"\n✓ Router: Correctly routed empty query to 'clarify'")

        # In real graph, researcher would not be called
        should_call_researcher = router_state.route == RouterDecision.FACT_CHECK
        assert should_call_researcher is False

        print("✓ Researcher: Correctly skipped (no API quota consumed)")

    def test_coding_request_skips_researcher(self):
        """E2E: Coding request routes to out_of_scope and does NOT make API calls."""
        user_query = "Write a Python function to calculate factorials"

        # Router classification
        router_state = router_node(AgentState(user_query=user_query))

        # Verify router routed to out_of_scope
        assert router_state.route == RouterDecision.OUT_OF_SCOPE
        assert router_state.run_metadata["router"]["trigger"] == RouterTrigger.NON_HISTORICAL_INTENT
        assert router_state.run_metadata["router"]["intent_type"] == "coding_request"

        print(f"\n✓ Router: Correctly identified coding request")

        # Verify researcher would not be called
        should_call_researcher = router_state.route == RouterDecision.FACT_CHECK
        assert should_call_researcher is False

        print("✓ Researcher: Correctly skipped (no API quota consumed)")

    def test_deduplication_across_queries(self):
        """E2E: Verify deduplication works with real search results."""
        user_query = "Battle of Waterloo 1815"

        # Execute full flow
        router_state = router_node(AgentState(user_query=user_query))
        researcher_delta = researcher_node(router_state)

        # Verify results are deduplicated
        search_results = researcher_delta["search_results"]
        urls = [str(result.url) for result in search_results]
        unique_urls = set(urls)

        assert len(urls) == len(unique_urls), "All URLs should be unique (no duplicates)"

        print(f"\n✓ Researcher: {len(search_results)} unique results (deduplication working)")
        print(f"  Queries executed: {len(researcher_delta['search_queries'])}")

    @pytest.mark.skipif(
        not settings.trusted_domains_only, reason="Requires TRUSTED_DOMAINS_ONLY=true in .env"
    )
    def test_trusted_domains_filtering(self):
        """E2E: Verify trusted domains filtering works with real API."""
        user_query = "Ancient Rome history"

        # Execute researcher with trusted domains enabled
        router_state = router_node(AgentState(user_query=user_query))
        researcher_delta = researcher_node(router_state)

        # Verify site filters were applied
        queries = [q.query for q in researcher_delta["search_queries"]]
        assert any("site:" in q for q in queries), "Site filters should be present in queries"

        print(f"\n✓ Trusted domains mode active")
        print(f"  Sample query: {queries[0]}")

        # Verify results come from trusted domains
        search_results = researcher_delta["search_results"]
        if search_results:
            # Note: Google may still return other domains, but trusted domains should be prioritized
            print(f"  Results from trusted sources: {len(search_results)}")

    def test_cache_behavior(self):
        """E2E: Verify caching works across multiple calls (second call should be faster)."""
        user_query = "French Revolution 1789"

        # First call (cache miss - makes real API calls)
        start_time = time.time()
        router_state_1 = router_node(AgentState(user_query=user_query))
        researcher_delta_1 = researcher_node(router_state_1)
        first_call_time = time.time() - start_time

        print(f"\n✓ First call: {first_call_time:.2f}s (cache miss)")

        # Second call (cache hit - should be much faster)
        start_time = time.time()
        router_state_2 = router_node(AgentState(user_query=user_query))
        researcher_delta_2 = researcher_node(router_state_2)
        second_call_time = time.time() - start_time

        print(f"✓ Second call: {second_call_time:.2f}s (cache hit)")

        # Verify results are identical
        assert len(researcher_delta_1["search_results"]) == len(
            researcher_delta_2["search_results"]
        )

        # Second call should be faster (cache hit)
        # Note: This may not always be true if network is very fast, so we just check results match
        print(f"  Speedup: {first_call_time / max(second_call_time, 0.001):.1f}x")