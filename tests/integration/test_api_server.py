"""Integration tests for the FastAPI server.

Tests the /api/chat endpoint which is the main endpoint for the React frontend.
Uses either mock or real backend based on settings.use_mock configuration.
"""

import pytest
from fastapi.testclient import TestClient


class TestApiServer:
    """Integration tests for the FastAPI server."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        """Setup test environment with mock mode enabled."""
        # Force mock mode for tests
        monkeypatch.setenv("USE_MOCK", "true")

        # Re-import the app after setting env var
        # This is needed because settings are loaded at import time
        import importlib

        import src.check_it_ai.api.server
        import src.check_it_ai.config

        importlib.reload(src.check_it_ai.config)
        importlib.reload(src.check_it_ai.api.server)

        from src.check_it_ai.api.server import app

        self.client = TestClient(app)

    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["mode"] in ["mock", "real"]
        assert "version" in data

    def test_chat_endpoint_basic(self):
        """Test the /api/chat endpoint with a basic query."""
        response = self.client.post(
            "/api/chat", json={"query": "Is the Earth round?", "mode": "standard"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check required fields exist
        assert "answer" in data
        assert "citations" in data
        assert "evidence" in data
        assert "metadata" in data
        assert "route" in data

        # Check evidence structure
        assert "items" in data["evidence"]
        assert "overall_verdict" in data["evidence"]

        # Check metadata
        assert "latency_ms" in data["metadata"]
        assert "confidence" in data["metadata"]

    def test_chat_endpoint_mock_true(self):
        """Test chat with mock:true trigger for supported verdict."""
        response = self.client.post(
            "/api/chat", json={"query": "mock:true The sky is blue", "mode": "standard"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["metadata"]["confidence"] == 0.98
        assert data["metadata"]["is_mock"] is True
        assert len(data["citations"]) > 0

    def test_chat_endpoint_mock_false(self):
        """Test chat with mock:false trigger for unsupported verdict."""
        response = self.client.post(
            "/api/chat", json={"query": "mock:false Claim", "mode": "standard"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["metadata"]["confidence"] == 0.95
        assert "debunked" in data["answer"]

    def test_chat_endpoint_empty_query_validation(self):
        """Test that empty queries return 422 Unprocessable Entity."""
        response = self.client.post("/api/chat", json={"query": "", "mode": "standard"})

        # Pydantic validation catches empty string (min_length=1)
        assert response.status_code == 422
        assert "String should have at least 1 character" in response.json()["detail"][0]["msg"]

    def test_chat_endpoint_animated_mode(self):
        """Test that animated mode is accepted."""
        response = self.client.post("/api/chat", json={"query": "Test query", "mode": "animated"})

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["mode"] == "animated"
