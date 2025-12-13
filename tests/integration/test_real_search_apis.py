"""Integration tests for real search APIs (not mocked).

These tests make actual API calls and should only be run when:
1. API credentials are configured in .env
2. You want to verify the APIs work end-to-end
3. You're okay with using API quota

Run with: pytest tests/integration/test_real_search_apis.py -v -s

Skip with: pytest tests/ --ignore=tests/integration/
"""

import pytest

from src.check_it_ai.config import settings
from src.check_it_ai.tools.duckduckgo_search import duckduckgo_search
from src.check_it_ai.tools.fact_check_api import google_fact_check
from src.check_it_ai.tools.google_search import google_search
from src.check_it_ai.types.search import SearchResult


@pytest.mark.integration
class TestRealGoogleSearch:
    """Integration tests for Google Custom Search API."""

    def test_google_search_real_api(self):
        """Test Google Search with real API call."""
        # Skip if credentials not configured
        if not settings.google_api_key or not settings.google_cse_id:
            pytest.skip("Google API credentials not configured")

        # Make real API call
        query = "Python programming language"
        results = google_search(query, num_results=5)

        # Assertions
        assert isinstance(results, list)
        assert len(results) > 0, "Should return at least one result"
        assert len(results) <= 5, "Should not exceed requested num_results"

        # Check first result structure
        first_result = results[0]
        assert isinstance(first_result, SearchResult)
        assert first_result.title, "Result should have a title"
        assert first_result.snippet, "Result should have a snippet"
        assert str(first_result.url).startswith("http"), "Result should have valid URL"
        assert first_result.display_domain, "Result should have display_domain"
        assert first_result.rank == 1, "First result should have rank 1"

        # Print results for manual verification
        print(f"\n✅ Google Search Results for '{query}':")
        for result in results:
            print(f"  [{result.rank}] {result.title}")
            print(f"      {result.url}")
            print(f"      {result.snippet[:100]}...")

    def test_google_search_hebrew_query(self):
        """Test Google Search with Hebrew query."""
        if not settings.google_api_key or not settings.google_cse_id:
            pytest.skip("Google API credentials not configured")

        # Hebrew query
        query = "פייתון שפת תכנות"  # "Python programming language" in Hebrew
        results = google_search(query, num_results=3)

        assert len(results) > 0, "Should return results for Hebrew query"

        print(f"\n✅ Google Search Results for Hebrew query '{query}':")
        for result in results:
            print(f"  [{result.rank}] {result.title}")
            print(f"      {result.url}")


@pytest.mark.integration
class TestRealFactCheckAPI:
    """Integration tests for Google Fact Check Tools API."""

    def test_fact_check_api_real_call(self):
        """Test Fact Check API with real API call."""
        if not settings.google_api_key:
            pytest.skip("Google API key not configured")

        # Query about a commonly fact-checked topic
        query = "COVID-19 vaccine safety"
        results = google_fact_check(query, num_results=5, language_code="en")

        # Note: Fact Check API may return 0 results for some queries
        # This is expected behavior, not an error
        print(f"\n✅ Fact Check API Results for '{query}':")
        if results:
            assert all(isinstance(r, SearchResult) for r in results)
            assert all("[FACT-CHECK]" in r.title for r in results)

            for result in results:
                print(f"  [{result.rank}] {result.title}")
                print(f"      {result.url}")
                print(f"      {result.snippet[:100]}...")
        else:
            print("  ⚠️  No fact-check results found (this is normal for some queries)")

    def test_fact_check_api_hebrew_with_fallback(self):
        """Test Fact Check API with Hebrew query and fallback to English."""
        if not settings.google_api_key:
            pytest.skip("Google API key not configured")

        # Hebrew query about a fact-checked topic
        query = "חיסון קורונה"  # "Corona vaccine" in Hebrew

        # Try Hebrew first
        results_he = google_fact_check(query, num_results=5, language_code="he")
        print(f"\n✅ Fact Check API Results for Hebrew query '{query}':")
        print(f"   Hebrew results: {len(results_he)}")

        # If no Hebrew results, try English fallback
        if not results_he:
            print("   ⚠️  No Hebrew fact-checks, trying English fallback...")
            results_en = google_fact_check(query, num_results=5, language_code="en")
            print(f"   English results: {len(results_en)}")

            if results_en:
                print("   ✅ Fallback successful! Got English fact-checks:")
                for result in results_en[:3]:  # Show first 3
                    print(f"      [{result.rank}] {result.title}")
        else:
            print("   ✅ Found Hebrew fact-checks:")
            for result in results_he:
                print(f"      [{result.rank}] {result.title}")


@pytest.mark.integration
class TestRealDuckDuckGoSearch:
    """Integration tests for DuckDuckGo search (no API key needed)."""

    def test_duckduckgo_search_real_call(self):
        """Test DuckDuckGo search with real API call."""
        query = "Python programming"
        results = duckduckgo_search(query, num_results=5)

        if not results:
            # Fallback to another broad query if first one fails
            print("   ⚠️  No results for 'Python programming', trying 'Google'...")
            query = "Google"
            results = duckduckgo_search(query, num_results=5)

        assert isinstance(results, list)
        assert len(results) > 0, "Should return at least one result"

        # Check first result structure
        first_result = results[0]
        assert isinstance(first_result, SearchResult)
        assert first_result.title, "Result should have a title"
        assert first_result.snippet, "Result should have a snippet"
        assert str(first_result.url).startswith("http"), "Result should have valid URL"

        print(f"\n✅ DuckDuckGo Search Results for '{query}':")
        for result in results:
            print(f"  [{result.rank}] {result.title}")
            print(f"      {result.url}")

    def test_duckduckgo_hebrew_query(self):
        """Test DuckDuckGo search with Hebrew query."""
        # Use a very broad query to ensure results
        query = "ישראל"  # "Israel"
        results = duckduckgo_search(query, num_results=3)

        if not results:
            # Fallback to another common query if first one fails (flakiness mitigation)
            query = "חדשות"  # "News"
            results = duckduckgo_search(query, num_results=3)

        assert len(results) > 0, "Should return results for Hebrew query"

        print(f"\n✅ DuckDuckGo Results for Hebrew query '{query}':")
        for result in results:
            print(f"  [{result.rank}] {result.title}")


@pytest.mark.integration
class TestMultiSourceWorkflow:
    """Test the multi-source search strategy recommended for Researcher Node."""

    def test_multi_source_search_workflow(self):
        """Test searching across all sources with fallbacks."""
        query = "climate change"

        all_results = []
        sources_used = []

        print(f"\n✅ Multi-Source Search for '{query}':")

        # Source 1: Fact Check API (if configured)
        if settings.google_api_key and settings.use_fact_check_api:
            try:
                fact_checks = google_fact_check(query, num_results=3, language_code="en")
                all_results.extend(fact_checks)
                sources_used.append("Fact Check API")
                print(f"  ✅ Fact Check API: {len(fact_checks)} results")
            except Exception as e:
                print(f"  ⚠️  Fact Check API failed: {e}")

        # Source 2: Google Search (if configured)
        if settings.google_api_key and settings.google_cse_id:
            try:
                google_results = google_search(query, num_results=5)
                all_results.extend(google_results)
                sources_used.append("Google Search")
                print(f"  ✅ Google Search: {len(google_results)} results")
            except Exception as e:
                print(f"  ⚠️  Google Search failed: {e}")

        # Source 3: DuckDuckGo (always available, no credentials needed)
        try:
            ddg_results = duckduckgo_search(query, num_results=5)
            all_results.extend(ddg_results)
            sources_used.append("DuckDuckGo")
            print(f"  ✅ DuckDuckGo: {len(ddg_results)} results")
        except Exception as e:
            print(f"  ⚠️  DuckDuckGo failed: {e}")

        # Assertions
        assert len(all_results) > 0, "Should get results from at least one source"
        assert len(sources_used) > 0, "Should successfully use at least one source"

        print(f"\n  📊 Total Results: {len(all_results)}")
        print(f"  📊 Sources Used: {', '.join(sources_used)}")

        # Show sample of combined results
        print("\n  Sample Combined Results:")
        for result in all_results[:5]:
            prefix = "[FACT-CHECK]" if "[FACT-CHECK]" in result.title else "[WEB]"
            print(f"    {prefix} {result.title[:80]}...")
