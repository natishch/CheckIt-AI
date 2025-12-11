"""Tests for Google Fact Check Tools API client with caching."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from check_it_ai.tools.fact_check_api import FactCheckClient, FactCheckQuotaError
from check_it_ai.types.schemas import SearchResult
from check_it_ai.utils.cache import SearchCache


class TestFactCheckClient:
    """Test suite for FactCheckClient."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path: Path) -> Path:
        """Create a temporary cache directory for testing."""
        cache_dir = tmp_path / "test_cache_factcheck"
        cache_dir.mkdir()
        return cache_dir

    @pytest.fixture
    def mock_cache(self, temp_cache_dir: Path) -> SearchCache:
        """Create a SearchCache instance for testing."""
        return SearchCache(cache_dir=temp_cache_dir, ttl_hours=24)

    @pytest.fixture
    def client(self, mock_cache: SearchCache) -> FactCheckClient:
        """Create a FactCheckClient instance for testing."""
        return FactCheckClient(
            api_key="test_api_key",
            language_code="en",
            cache=mock_cache,
        )

    @pytest.fixture
    def mock_fact_check_response(self) -> dict:
        """Create a mock Fact Check API response."""
        return {
            "claims": [
                {
                    "text": "World War II ended in 1945",
                    "claimant": "Test Source",
                    "claimDate": "2024-01-15",
                    "claimReview": [
                        {
                            "publisher": {"name": "PolitiFact", "site": "politifact.com"},
                            "url": "https://www.politifact.com/factchecks/2024/jan/15/wwii-end/",
                            "title": "Yes, World War II ended in 1945",
                            "textualRating": "True",
                            "languageCode": "en",
                            "reviewDate": "2024-01-20",
                        }
                    ],
                },
                {
                    "text": "The moon landing was faked",
                    "claimant": "Conspiracy Theorist",
                    "claimDate": "2023-12-01",
                    "claimReview": [
                        {
                            "publisher": {"name": "Snopes", "site": "snopes.com"},
                            "url": "https://www.snopes.com/fact-check/moon-landing-fake/",
                            "title": "Moon landing was real, not faked",
                            "textualRating": "False",
                            "languageCode": "en",
                            "reviewDate": "2023-12-05",
                        }
                    ],
                },
            ]
        }

    @pytest.fixture
    def mock_empty_response(self) -> dict:
        """Create a mock empty Fact Check API response."""
        return {"claims": []}

    def test_client_initialization(self, client: FactCheckClient):
        """Test that client initializes with correct parameters."""
        assert client.api_key == "test_api_key"
        assert client.language_code == "en"
        assert client.cache is not None

    def test_search_with_empty_query_raises_error(self, client: FactCheckClient):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            client.search("")

        with pytest.raises(ValueError, match="Search query cannot be empty"):
            client.search("   ")

    def test_search_with_invalid_num_results_raises_error(self, client: FactCheckClient):
        """Test that invalid num_results raises ValueError."""
        with pytest.raises(ValueError, match="num_results must be between 1 and 100"):
            client.search("test query", num_results=0)

        with pytest.raises(ValueError, match="num_results must be between 1 and 100"):
            client.search("test query", num_results=101)

    @patch("httpx.Client")
    def test_successful_fact_check_search(
        self,
        mock_httpx_client: Mock,
        client: FactCheckClient,
        mock_fact_check_response: dict,
    ):
        """Test successful Fact Check API search with mocked response."""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_fact_check_response
        mock_response.raise_for_status = Mock()

        # Mock httpx client context manager
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # Execute search
        results = client.search("World War II end date", num_results=10)

        # Assertions
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

        # Check first result (True rating)
        assert "[FACT-CHECK]" in results[0].title
        assert "World War II ended in 1945" in results[0].title
        assert "Rating: True" in results[0].snippet
        assert str(results[0].url) == "https://www.politifact.com/factchecks/2024/jan/15/wwii-end/"
        assert (
            "politifact" in results[0].display_domain.lower()
            or results[0].display_domain == "PolitiFact"
        )
        assert results[0].rank == 1

        # Check second result (False rating)
        assert "[FACT-CHECK]" in results[1].title
        assert "moon landing" in results[1].title.lower()
        assert "Rating: False" in results[1].snippet
        assert str(results[1].url) == "https://www.snopes.com/fact-check/moon-landing-fake/"
        assert results[1].rank == 2

        # Verify API was called correctly
        mock_client_instance.get.assert_called_once()
        call_args = mock_client_instance.get.call_args
        assert "key" in call_args[1]["params"]
        assert call_args[1]["params"]["query"] == "World War II end date"

    @patch("httpx.Client")
    def test_empty_results_handling(
        self,
        mock_httpx_client: Mock,
        client: FactCheckClient,
        mock_empty_response: dict,
    ):
        """Test handling of empty Fact Check API results."""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_empty_response
        mock_response.raise_for_status = Mock()

        # Mock httpx client context manager
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # Execute search
        results = client.search("obscure historical event", num_results=10)

        # Assertions
        assert len(results) == 0
        assert results == []

    @patch("httpx.Client")
    def test_quota_error_403(self, mock_httpx_client: Mock, client: FactCheckClient):
        """Test handling of 403 quota error."""
        # Mock httpx response with 403 status
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": {"message": "API key quota exceeded"}}

        # Mock httpx client context manager
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # Execute search and expect FactCheckQuotaError
        with pytest.raises(FactCheckQuotaError, match="API quota exceeded"):
            client.search("test query", num_results=10)

    @patch("httpx.Client")
    def test_quota_error_429(self, mock_httpx_client: Mock, client: FactCheckClient):
        """Test handling of 429 quota error."""
        # Mock httpx response with 429 status
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}

        # Mock httpx client context manager
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # Execute search and expect FactCheckQuotaError
        with pytest.raises(FactCheckQuotaError, match="API quota exceeded"):
            client.search("test query", num_results=10)

    @patch("httpx.Client")
    def test_caching_behavior(
        self,
        mock_httpx_client: Mock,
        client: FactCheckClient,
        mock_fact_check_response: dict,
    ):
        """Test that results are cached and reused on subsequent requests."""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_fact_check_response
        mock_response.raise_for_status = Mock()

        # Mock httpx client context manager
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # First search - should hit API
        results1 = client.search("World War II", num_results=10)
        assert len(results1) == 2
        assert mock_client_instance.get.call_count == 1

        # Second search with same query - should use cache
        results2 = client.search("World War II", num_results=10)
        assert len(results2) == 2
        assert mock_client_instance.get.call_count == 1  # Still 1, no new API call

        # Verify results are identical
        assert results1[0].title == results2[0].title
        assert results1[0].url == results2[0].url

    @patch("httpx.Client")
    def test_cache_miss_on_different_query(
        self,
        mock_httpx_client: Mock,
        client: FactCheckClient,
        mock_fact_check_response: dict,
    ):
        """Test that different queries result in cache miss."""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_fact_check_response
        mock_response.raise_for_status = Mock()

        # Mock httpx client context manager
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # First search
        results1 = client.search("World War II", num_results=10)
        assert len(results1) == 2
        assert mock_client_instance.get.call_count == 1

        # Second search with different query - should hit API again
        results2 = client.search("Moon Landing", num_results=10)
        assert len(results2) == 2
        assert mock_client_instance.get.call_count == 2  # New API call

    @patch("httpx.Client")
    def test_http_timeout_error(self, mock_httpx_client: Mock, client: FactCheckClient):
        """Test handling of HTTP timeout error."""
        # Mock httpx client to raise TimeoutException
        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = httpx.TimeoutException("Request timeout")
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # Execute search - should return empty list on error (graceful degradation)
        results = client.search("test query", num_results=10)
        assert results == []

    @patch("httpx.Client")
    def test_malformed_claim_skipped(
        self,
        mock_httpx_client: Mock,
        client: FactCheckClient,
    ):
        """Test that malformed claims are skipped during parsing."""
        # Mock response with one valid and one malformed claim
        mock_response_data = {
            "claims": [
                {
                    "text": "Valid claim",
                    "claimReview": [
                        {
                            "publisher": {"name": "FactChecker"},
                            "url": "https://factchecker.com/valid",
                            "title": "Valid fact-check",
                            "textualRating": "True",
                        }
                    ],
                },
                {
                    "text": "Malformed claim - no review"
                    # Missing claimReview
                },
                {
                    "text": "Another malformed - no URL",
                    "claimReview": [
                        {
                            "publisher": {"name": "BadChecker"},
                            # Missing url
                            "title": "Bad fact-check",
                            "textualRating": "False",
                        }
                    ],
                },
            ]
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # Execute search
        results = client.search("test query", num_results=10)

        # Only valid claim should be returned
        assert len(results) == 1
        assert "Valid claim" in results[0].title
        assert str(results[0].url) == "https://factchecker.com/valid"

    @patch("httpx.Client")
    def test_fact_check_prefix_in_titles(
        self,
        mock_httpx_client: Mock,
        client: FactCheckClient,
        mock_fact_check_response: dict,
    ):
        """Test that all results have [FACT-CHECK] prefix in title."""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_fact_check_response
        mock_response.raise_for_status = Mock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # Execute search
        results = client.search("test query", num_results=10)

        # All results should have [FACT-CHECK] prefix
        assert all("[FACT-CHECK]" in r.title for r in results)

    @patch("httpx.Client")
    def test_rating_in_snippet(
        self,
        mock_httpx_client: Mock,
        client: FactCheckClient,
        mock_fact_check_response: dict,
    ):
        """Test that textual rating is included in snippet."""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_fact_check_response
        mock_response.raise_for_status = Mock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # Execute search
        results = client.search("test query", num_results=10)

        # All snippets should contain "Rating:"
        assert all("Rating:" in r.snippet for r in results)

        # Check specific ratings
        assert "Rating: True" in results[0].snippet
        assert "Rating: False" in results[1].snippet
