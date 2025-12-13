"""Tests for Google Search API client with caching and fallback."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from src.check_it_ai.tools.google_search import GoogleSearchClient
from src.check_it_ai.types.search import SearchResult
from src.check_it_ai.utils.cache import SearchCache


class TestGoogleSearchClient:
    """Test suite for GoogleSearchClient."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path: Path) -> Path:
        """Create a temporary cache directory for testing."""
        cache_dir = tmp_path / "test_cache"
        cache_dir.mkdir()
        return cache_dir

    @pytest.fixture
    def mock_cache(self, temp_cache_dir: Path) -> SearchCache:
        """Create a SearchCache instance for testing."""
        return SearchCache(cache_dir=temp_cache_dir, ttl_hours=24)

    @pytest.fixture
    def client(self, mock_cache: SearchCache) -> GoogleSearchClient:
        """Create a GoogleSearchClient instance for testing."""
        return GoogleSearchClient(
            api_key="test_api_key",
            cse_id="test_cse_id",
            cache=mock_cache,
        )

    @pytest.fixture
    def mock_google_response(self) -> dict:
        """Create a mock Google API response."""
        return {
            "items": [
                {
                    "title": "World War II - Wikipedia",
                    "snippet": "World War II ended in 1945...",
                    "link": "https://en.wikipedia.org/wiki/World_War_II",
                    "displayLink": "en.wikipedia.org",
                },
                {
                    "title": "WW2 History",
                    "snippet": "Comprehensive history of World War II",
                    "link": "https://www.history.com/topics/world-war-ii",
                    "displayLink": "history.com",
                },
            ]
        }

    def test_client_initialization(self, client: GoogleSearchClient):
        """Test that client initializes with correct parameters."""
        assert client.api_key == "test_api_key"
        assert client.cse_id == "test_cse_id"
        assert client.cache is not None

    def test_search_with_empty_query_raises_error(self, client: GoogleSearchClient):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            client.search("")

        with pytest.raises(ValueError, match="Search query cannot be empty"):
            client.search("   ")

    def test_search_with_invalid_num_results_raises_error(self, client: GoogleSearchClient):
        """Test that invalid num_results raises ValueError."""
        with pytest.raises(ValueError, match="num_results must be between 1 and 100"):
            client.search("test query", num_results=0)

        with pytest.raises(ValueError, match="num_results must be between 1 and 100"):
            client.search("test query", num_results=101)

    @patch("httpx.Client")
    def test_successful_google_search(
        self,
        mock_httpx_client: Mock,
        client: GoogleSearchClient,
        mock_google_response: dict,
    ):
        """Test successful Google search with mocked API response."""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_google_response
        mock_response.raise_for_status = Mock()

        # Mock httpx client context manager
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # Execute search
        results = client.search("World War II", num_results=10)

        # Verify results
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].title == "World War II - Wikipedia"
        assert results[0].snippet == "World War II ended in 1945..."
        assert str(results[0].url) == "https://en.wikipedia.org/wiki/World_War_II"
        assert results[0].display_domain == "en.wikipedia.org"
        assert results[0].rank == 1
        assert results[1].rank == 2

    @patch("src.check_it_ai.tools.google_search.make_api_request")
    def test_quota_error_403(
        self,
        mock_make_request: Mock,
        client: GoogleSearchClient,
    ):
        """Test that 403 status code raises QuotaError."""
        # Mock quota exceeded error from shared utility
        from src.check_it_ai.tools._http_utils import QuotaExceededError

        mock_make_request.side_effect = QuotaExceededError(
            "API quota exceeded: Quota exceeded for quota metric (status: 403)"
        )

        # Verify exception is raised (QuotaError is an alias for QuotaExceededError)
        with pytest.raises(QuotaExceededError, match="API quota exceeded"):
            client.search("test query")

    @patch("src.check_it_ai.tools.google_search.make_api_request")
    def test_quota_error_429(
        self,
        mock_make_request: Mock,
        client: GoogleSearchClient,
    ):
        """Test that 429 status code raises QuotaError."""
        # Mock quota exceeded error from shared utility
        from src.check_it_ai.tools._http_utils import QuotaExceededError

        mock_make_request.side_effect = QuotaExceededError(
            "API quota exceeded: Rate limit exceeded (status: 429)"
        )

        # Verify exception is raised (QuotaError is an alias for QuotaExceededError)
        with pytest.raises(QuotaExceededError, match="API quota exceeded"):
            client.search("test query")

    @patch("httpx.Client")
    def test_cache_hit(
        self,
        mock_httpx_client: Mock,
        client: GoogleSearchClient,
        mock_google_response: dict,
    ):
        """Test that cache hit returns cached results without API call."""
        # First search - populate cache
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_google_response
        mock_response.raise_for_status = Mock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        results1 = client.search("World War II", num_results=10)
        assert len(results1) == 2

        # Reset mock to verify no second API call
        mock_client_instance.get.reset_mock()

        # Second search - should hit cache
        results2 = client.search("World War II", num_results=10)

        # Verify cache hit
        assert len(results2) == 2
        assert results1[0].title == results2[0].title
        mock_client_instance.get.assert_not_called()

    @patch("httpx.Client")
    def test_cache_miss_different_query(
        self,
        mock_httpx_client: Mock,
        client: GoogleSearchClient,
        mock_google_response: dict,
    ):
        """Test that different queries result in cache miss."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_google_response
        mock_response.raise_for_status = Mock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # First search
        client.search("World War II", num_results=10)

        # Second search with different query
        client.search("World War I", num_results=10)

        # Verify API was called twice
        assert mock_client_instance.get.call_count == 2

    @patch("httpx.Client")
    def test_http_timeout_error(
        self,
        mock_httpx_client: Mock,
        client: GoogleSearchClient,
    ):
        """Test that timeout errors are properly raised."""
        # Mock timeout
        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = httpx.TimeoutException("Timeout")
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # Verify timeout error is raised
        with pytest.raises(httpx.TimeoutException):
            client.search("test query")

    @patch("httpx.Client")
    def test_parse_results_with_invalid_item(
        self,
        mock_httpx_client: Mock,
        client: GoogleSearchClient,
    ):
        """Test that invalid search results are skipped during parsing."""
        # Mock response with one valid and one invalid item
        mock_response_data = {
            "items": [
                {
                    "title": "Valid Result",
                    "snippet": "Valid snippet",
                    "link": "https://example.com",
                    "displayLink": "example.com",
                },
                {
                    "title": "Invalid Result",
                    "snippet": "No URL provided",
                    # Missing 'link' field - will fail validation
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
        results = client.search("test query")

        # Verify only valid result is returned
        assert len(results) == 1
        assert results[0].title == "Valid Result"

    @patch("httpx.Client")
    def test_empty_search_results(
        self,
        mock_httpx_client: Mock,
        client: GoogleSearchClient,
    ):
        """Test handling of empty search results from API."""
        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = Mock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # Execute search
        results = client.search("obscure query")

        # Verify empty results
        assert results == []
