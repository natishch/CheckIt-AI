"""Integration tests for real API calls (not mocked).

These tests are marked with @pytest.mark.integration and should be run separately
from unit tests when you want to verify real API functionality.

Run integration tests:
    pytest tests/integration/ -v -s -m integration

Skip integration tests during regular testing:
    pytest tests/ --ignore=tests/integration/
"""
