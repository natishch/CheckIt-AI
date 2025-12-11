from fastapi.testclient import TestClient

from check_it_ai.api.server import app
from check_it_ai.types.schemas import FinalOutput

client = TestClient(app)


class TestApiServer:
    """Integration tests for the FastAPI server with Mock Backend."""

    def test_health_check(self):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "mode": "mock"}

    def test_check_claim_mock_true(self):
        """Test checking a claim that triggers a mocked TRUE response."""
        response = client.post("/api/check", json={"text": "mock:true claim"})

        assert response.status_code == 200
        data = response.json()

        # Validate structure against Pydantic schema
        result = FinalOutput(**data)
        assert result.confidence == 0.98
        assert "Scientific consensus" in result.answer
        assert len(result.citations) == 2

    def test_check_claim_mock_false(self):
        """Test checking a claim that triggers a mocked FALSE response."""
        response = client.post("/api/check", json={"text": "mock:false claim"})

        assert response.status_code == 200
        data = response.json()

        result = FinalOutput(**data)
        assert result.confidence == 0.95
        assert "debunked" in result.answer

    def test_empty_claim_validation(self):
        """Test that empty queries return 400 Bad Request."""
        response = client.post("/api/check", json={"text": ""})
        # Pydantic validation catches empty string (min_length=1) -> 422 Unprocessable Entity
        assert response.status_code == 422
        assert "String should have at least 1 character" in response.json()["detail"][0]["msg"]
