"""Unit tests for the Researcher Node with query expansion and deduplication."""

from unittest.mock import patch

import pytest

from check_it_ai.graph.nodes.researcher import (
    deduplicate_by_url,
    expand_query,
    researcher_node,
)
from check_it_ai.graph.state import AgentState
from check_it_ai.types.schemas import SearchResult


class TestQueryExpansion:
    """Test suite for query expansion logic."""

    def test_expand_query_basic(self):
        """Test that a simple query expands into 3 diverse queries."""
        user_query = "When did World War II end?"
        expanded = expand_query(user_query, trusted_sources_only=False)

        assert len(expanded) == 3
        assert expanded[0] == "When did World War II end?"
        assert "history" in expanded[1].lower()
        assert "facts" in expanded[2].lower()

    def test_expand_query_with_history_keyword(self):
        """Test that queries already containing 'history' don't get it added again."""
        user_query = "History of World War II"
        expanded = expand_query(user_query, trusted_sources_only=False)

        assert len(expanded) <= 3
        # Should have original query
        assert "History of World War II" in expanded[0]
        # Should skip adding 'history' again, but add 'facts'
        assert any("facts" in q.lower() for q in expanded)

    def test_expand_query_with_fact_keyword(self):
        """Test that queries already containing 'fact' don't get 'facts' added."""
        user_query = "Facts about the moon landing"
        expanded = expand_query(user_query, trusted_sources_only=False)

        assert len(expanded) <= 3
        # Should have original query
        assert "Facts about the moon landing" in expanded[0]
        # Should add 'history' but not duplicate 'facts'
        assert any("history" in q.lower() for q in expanded)

    def test_expand_query_empty_string(self):
        """Test that empty query returns empty list."""
        assert expand_query("", trusted_sources_only=False) == []
        assert expand_query("   ", trusted_sources_only=False) == []

    def test_expand_query_trusted_sources_mode(self):
        """Test that trusted_sources_only appends site filters."""
        user_query = "Napoleon Bonaparte"
        expanded = expand_query(user_query, trusted_sources_only=True)

        assert len(expanded) == 3
        # All queries should have site filters
        for query in expanded:
            assert "site:wikipedia.org" in query or "site:britannica.com" in query
            assert "site:.edu" in query or "site:.gov" in query

    def test_expand_query_preserves_user_query_in_all_variants(self):
        """Test that all expanded queries contain the original user query."""
        user_query = "Battle of Waterloo"
        expanded = expand_query(user_query, trusted_sources_only=False)

        for query in expanded:
            assert "Battle of Waterloo" in query


class TestDeduplication:
    """Test suite for URL deduplication logic."""

    @pytest.fixture
    def duplicate_results(self) -> list[SearchResult]:
        """Create a list of search results with duplicate URLs."""
        return [
            SearchResult(
                title="Result 1",
                snippet="First occurrence",
                url="https://example.com/page1",
                display_domain="example.com",
                rank=1,
            ),
            SearchResult(
                title="Result 2",
                snippet="Unique result",
                url="https://example.com/page2",
                display_domain="example.com",
                rank=2,
            ),
            SearchResult(
                title="Result 1 Duplicate",
                snippet="Second occurrence (should be removed)",
                url="https://example.com/page1",  # Duplicate URL
                display_domain="example.com",
                rank=3,
            ),
            SearchResult(
                title="Result 3",
                snippet="Another unique result",
                url="https://example.com/page3",
                display_domain="example.com",
                rank=4,
            ),
        ]

    def test_deduplicate_by_url_removes_duplicates(self, duplicate_results):
        """Test that duplicate URLs are removed, keeping first occurrence."""
        deduplicated = deduplicate_by_url(duplicate_results)

        # Should have 3 unique results (removed 1 duplicate)
        assert len(deduplicated) == 3

        # Check that URLs are unique
        urls = [str(result.url) for result in deduplicated]
        assert len(urls) == len(set(urls))

        # First occurrence should be kept (rank=1)
        assert deduplicated[0].rank == 1
        assert deduplicated[0].snippet == "First occurrence"

        # Duplicate (rank=3) should be removed
        ranks = [result.rank for result in deduplicated]
        assert 3 not in ranks

    def test_deduplicate_by_url_case_insensitive(self):
        """Test that deduplication is case-insensitive for URLs."""
        results = [
            SearchResult(
                title="Result 1",
                snippet="Lowercase URL",
                url="https://example.com/page1",
                display_domain="example.com",
                rank=1,
            ),
            SearchResult(
                title="Result 2",
                snippet="Uppercase URL (should be removed)",
                url="HTTPS://EXAMPLE.COM/PAGE1",  # Same URL, different case
                display_domain="example.com",
                rank=2,
            ),
        ]

        deduplicated = deduplicate_by_url(results)

        # Should only keep first occurrence
        assert len(deduplicated) == 1
        assert deduplicated[0].rank == 1

    def test_deduplicate_by_url_no_duplicates(self):
        """Test that deduplication works when there are no duplicates."""
        results = [
            SearchResult(
                title="Result 1",
                snippet="First result",
                url="https://example.com/page1",
                display_domain="example.com",
                rank=1,
            ),
            SearchResult(
                title="Result 2",
                snippet="Second result",
                url="https://example.com/page2",
                display_domain="example.com",
                rank=2,
            ),
        ]

        deduplicated = deduplicate_by_url(results)

        # Should keep all results
        assert len(deduplicated) == 2
        assert deduplicated[0].rank == 1
        assert deduplicated[1].rank == 2

    def test_deduplicate_by_url_empty_list(self):
        """Test that deduplication works with empty list."""
        assert deduplicate_by_url([]) == []


class TestResearcherNode:
    """Test suite for the full researcher_node function."""

    @pytest.fixture
    def mock_search_results(self) -> list[SearchResult]:
        """Create mock search results."""
        return [
            SearchResult(
                title="World War II - Wikipedia",
                snippet="World War II ended in 1945...",
                url="https://en.wikipedia.org/wiki/World_War_II",
                display_domain="en.wikipedia.org",
                rank=1,
            ),
            SearchResult(
                title="WW2 History",
                snippet="Comprehensive history of World War II",
                url="https://www.history.com/topics/world-war-ii",
                display_domain="history.com",
                rank=2,
            ),
        ]

    @patch("check_it_ai.graph.nodes.researcher.google_search")
    def test_researcher_node_basic_flow(self, mock_google_search, mock_search_results):
        """Test basic flow: expansion → execution → deduplication."""
        # Mock google_search to return deterministic results
        mock_google_search.return_value = mock_search_results

        # Create initial state
        initial_state = AgentState(user_query="When did World War II end?")

        # Execute researcher node
        result_state_dict = researcher_node(initial_state)

        # Verify query expansion (should create ~3 queries)
        assert len(result_state_dict["search_queries"]) == 3

        # Verify google_search was called 3 times (once per expanded query)
        assert mock_google_search.call_count == 3

        # Verify search results are populated
        assert len(result_state_dict["search_results"]) > 0

    @patch("check_it_ai.graph.nodes.researcher.google_search")
    def test_researcher_node_deduplication(self, mock_google_search):
        """Test that deduplication removes duplicate URLs from multiple queries."""
        # Mock google_search to return results with duplicates
        # Query 1 returns results with URL1, URL2
        # Query 2 returns results with URL1 (duplicate), URL3
        # Query 3 returns results with URL2 (duplicate), URL4

        query_1_results = [
            SearchResult(
                title="Result URL1 Query1",
                snippet="From query 1",
                url="https://example.com/url1",
                display_domain="example.com",
                rank=1,
            ),
            SearchResult(
                title="Result URL2 Query1",
                snippet="From query 1",
                url="https://example.com/url2",
                display_domain="example.com",
                rank=2,
            ),
        ]

        query_2_results = [
            SearchResult(
                title="Result URL1 Query2 (DUPLICATE)",
                snippet="From query 2",
                url="https://example.com/url1",  # Duplicate of URL1
                display_domain="example.com",
                rank=1,
            ),
            SearchResult(
                title="Result URL3 Query2",
                snippet="From query 2",
                url="https://example.com/url3",
                display_domain="example.com",
                rank=2,
            ),
        ]

        query_3_results = [
            SearchResult(
                title="Result URL2 Query3 (DUPLICATE)",
                snippet="From query 3",
                url="https://example.com/url2",  # Duplicate of URL2
                display_domain="example.com",
                rank=1,
            ),
            SearchResult(
                title="Result URL4 Query3",
                snippet="From query 3",
                url="https://example.com/url4",
                display_domain="example.com",
                rank=2,
            ),
        ]

        # Return different results for each call
        mock_google_search.side_effect = [query_1_results, query_2_results, query_3_results]

        # Create initial state
        initial_state = AgentState(user_query="Test query")

        # Execute researcher node
        result_state_dict = researcher_node(initial_state)

        # Verify deduplication: should have 4 unique URLs (URL1, URL2, URL3, URL4)
        # Total results = 6, but 2 are duplicates, so final = 4
        assert len(result_state_dict["search_results"]) == 4

        # Verify all URLs are unique
        urls = [str(result.url) for result in result_state_dict["search_results"]]
        assert len(urls) == len(set(urls))

        # Verify first occurrence is kept (URL1 from query 1, not query 2)
        url1_result = next(r for r in result_state_dict["search_results"] if "url1" in str(r.url))
        assert "Query1" in url1_result.title

    @patch("check_it_ai.graph.nodes.researcher.google_search")
    @patch("check_it_ai.graph.nodes.researcher.settings")
    def test_researcher_node_trusted_mode(self, mock_settings, mock_google_search, mock_search_results):
        """Test that trusted mode appends site filters to queries."""
        # Enable trusted_sources_only mode
        mock_settings.trusted_sources_only = True
        mock_settings.max_search_results = 10
        mock_google_search.return_value = mock_search_results

        # Create initial state
        initial_state = AgentState(user_query="Napoleon Bonaparte")

        # Execute researcher node
        result_state_dict = researcher_node(initial_state)

        # Verify that all search queries have site filters
        for search_query in result_state_dict["search_queries"]:
            query_str = search_query.query
            assert "site:" in query_str
            # Should contain at least one of the trusted domains
            assert any(
                domain in query_str
                for domain in ["wikipedia.org", "britannica.com", ".edu", ".gov"]
            )

    @patch("check_it_ai.graph.nodes.researcher.google_search")
    def test_researcher_node_empty_query(self, mock_google_search):
        """Test that empty query returns empty results."""
        # Create initial state with empty query
        initial_state = AgentState(user_query="")

        # Execute researcher node
        result_state_dict = researcher_node(initial_state)

        # Verify no queries were created
        assert len(result_state_dict["search_queries"]) == 0
        assert len(result_state_dict["search_results"]) == 0

        # Verify google_search was never called
        mock_google_search.assert_not_called()

    @patch("check_it_ai.graph.nodes.researcher.google_search")
    def test_researcher_node_handles_api_errors(self, mock_google_search):
        """Test that node continues even when some API calls fail."""
        # Mock google_search to fail on first call, succeed on others
        mock_google_search.side_effect = [
            Exception("API quota exceeded"),  # Query 1 fails
            [  # Query 2 succeeds
                SearchResult(
                    title="Result 1",
                    snippet="Success",
                    url="https://example.com/page1",
                    display_domain="example.com",
                    rank=1,
                )
            ],
            [  # Query 3 succeeds
                SearchResult(
                    title="Result 2",
                    snippet="Success",
                    url="https://example.com/page2",
                    display_domain="example.com",
                    rank=1,
                )
            ],
        ]

        # Create initial state
        initial_state = AgentState(user_query="Test query")

        # Execute researcher node
        result_state_dict = researcher_node(initial_state)

        # Should have results from 2 successful queries
        assert len(result_state_dict["search_results"]) == 2

        # Verify google_search was called 3 times (despite first failure)
        assert mock_google_search.call_count == 3
