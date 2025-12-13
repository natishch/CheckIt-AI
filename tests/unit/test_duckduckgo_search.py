"""Tests for DuckDuckGo search provider."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.check_it_ai.tools.duckduckgo_search import duckduckgo_search
from src.check_it_ai.types.search import SearchResult


class TestDuckDuckGoSearch:
    """Test suite for DuckDuckGo search provider."""

    def test_search_with_empty_query_raises_error(self):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            duckduckgo_search("")

        with pytest.raises(ValueError, match="Search query cannot be empty"):
            duckduckgo_search("   ")

    @patch("ddgs.DDGS")
    def test_successful_duckduckgo_search(self, mock_ddgs: Mock):
        """Test successful DuckDuckGo search with mocked response."""
        # Mock DuckDuckGo response
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [
            {
                "title": "Test Result 1",
                "body": "This is a snippet from DuckDuckGo",
                "href": "https://example.com/1",
            },
            {
                "title": "Test Result 2",
                "body": "Another snippet",
                "href": "https://example.org/2",
            },
        ]
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance

        # Execute search
        results = duckduckgo_search("test query", num_results=10)

        # Assertions
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

        # Check first result
        assert results[0].title == "Test Result 1"
        assert results[0].snippet == "This is a snippet from DuckDuckGo"
        assert str(results[0].url) == "https://example.com/1"
        assert results[0].display_domain == "example.com"
        assert results[0].rank == 1

        # Check second result
        assert results[1].title == "Test Result 2"
        assert results[1].snippet == "Another snippet"
        assert str(results[1].url) == "https://example.org/2"
        assert results[1].display_domain == "example.org"
        assert results[1].rank == 2

        # Verify DDGS was called correctly
        mock_ddgs_instance.text.assert_called_once_with("test query", max_results=10)

    @patch("ddgs.DDGS")
    def test_empty_results_handling(self, mock_ddgs: Mock):
        """Test handling of empty DuckDuckGo results."""
        # Mock empty response
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = []
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance

        # Execute search
        results = duckduckgo_search("obscure query", num_results=10)

        # Assertions
        assert len(results) == 0
        assert results == []

    def test_import_error_handling(self):
        """Test handling when ddgs is not installed."""
        # This test simulates the ImportError by temporarily hiding the module
        import sys

        ddg_module = sys.modules.get("ddgs")
        if ddg_module:
            sys.modules["ddgs"] = None

        try:
            results = duckduckgo_search("test query")
            assert results == []  # Should return empty list on import error
        finally:
            # Restore the module
            if ddg_module:
                sys.modules["ddgs"] = ddg_module

    @patch("ddgs.DDGS")
    def test_exception_handling(self, mock_ddgs: Mock):
        """Test graceful handling of exceptions."""
        # Mock DDGS to raise an exception
        mock_ddgs.return_value.__enter__.side_effect = Exception("Network error")

        # Execute search - should return empty list
        results = duckduckgo_search("test query", num_results=10)

        assert results == []

    @patch("ddgs.DDGS")
    def test_malformed_result_skipped(self, mock_ddgs: Mock):
        """Test that malformed results are skipped during parsing."""
        # Mock response with one valid and one malformed result
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [
            {
                "title": "Valid Result",
                "body": "Valid snippet",
                "href": "https://valid.com",
            },
            {
                "title": "Malformed - no href",
                "body": "Should be skipped",
                # Missing 'href' field
            },
            {
                "title": "Another valid",
                "body": "Another snippet",
                "href": "https://valid2.com",
            },
        ]
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance

        # Execute search
        results = duckduckgo_search("test query", num_results=10)

        # Only valid results should be returned
        assert len(results) == 2
        assert results[0].title == "Valid Result"
        assert results[1].title == "Another valid"
