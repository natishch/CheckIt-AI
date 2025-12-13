"""Tests for LLM provider factory.

These tests verify that:
1. Each provider creates the correct LLM type
2. Missing API keys raise appropriate errors
3. Unknown providers raise errors
4. Health check returns correct status

Note: Some tests require optional LangChain provider packages:
- langchain-openai
- langchain-anthropic
- langchain-google-genai

Tests are skipped if these packages aren't installed.
"""

from unittest.mock import MagicMock, patch

import langchain_anthropic
import langchain_google_genai
import langchain_openai
import pytest

from src.check_it_ai.config import Settings
from src.check_it_ai.llm.providers import (
    LLMProviderError,
    check_provider_health,
    get_writer_llm,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def base_settings() -> Settings:
    """Create base settings with minimal configuration."""
    return Settings(
        google_api_key="test-google-api",
        google_cse_id="test-cse-id",
        writer_llm_provider="local",
    )


@pytest.fixture
def openai_settings() -> Settings:
    """Create settings configured for OpenAI."""
    return Settings(
        google_api_key="test-google-api",
        google_cse_id="test-cse-id",
        writer_llm_provider="openai",
        openai_api_key="sk-test-key-12345",
        openai_model="gpt-4o-mini",
    )


@pytest.fixture
def anthropic_settings() -> Settings:
    """Create settings configured for Anthropic."""
    return Settings(
        google_api_key="test-google-api",
        google_cse_id="test-cse-id",
        writer_llm_provider="anthropic",
        anthropic_api_key="sk-ant-test-key-12345",
        anthropic_model="claude-3-5-sonnet-20241022",
    )


@pytest.fixture
def google_settings() -> Settings:
    """Create settings configured for Google Generative AI."""
    return Settings(
        google_api_key="test-google-api",
        google_cse_id="test-cse-id",
        writer_llm_provider="google",
        google_genai_api_key="test-genai-key",
        google_genai_model="gemini-1.5-flash",
    )


@pytest.fixture
def local_settings() -> Settings:
    """Create settings configured for local LLM."""
    return Settings(
        google_api_key="test-google-api",
        google_cse_id="test-cse-id",
        writer_llm_provider="local",
        local_llm_base_url="http://127.0.0.1:1234/v1",
        local_llm_model="local-model",
        local_llm_api_key="not-needed",
    )


# =============================================================================
# Test Unknown Provider
# =============================================================================


def test_unknown_provider_raises_error():
    """Unknown provider should raise LLMProviderError."""
    # Create settings with unknown provider - need to bypass Literal validation
    settings = Settings(
        google_api_key="test-google-api",
        google_cse_id="test-cse-id",
        writer_llm_provider="local",
    )
    # Directly set to bypass Pydantic Literal validation for testing
    settings.writer_llm_provider = "unknown_provider"

    with pytest.raises(LLMProviderError) as exc_info:
        get_writer_llm(settings)

    assert "Unknown LLM provider" in str(exc_info.value)
    assert "unknown_provider" in str(exc_info.value)


# =============================================================================
# Test OpenAI Provider
# =============================================================================


def test_openai_missing_api_key_raises_error():
    """OpenAI provider without API key should raise error."""
    settings = Settings(
        google_api_key="test-google-api",
        google_cse_id="test-cse-id",
        writer_llm_provider="openai",
        openai_api_key="",
    )

    with pytest.raises(LLMProviderError) as exc_info:
        get_writer_llm(settings)

    assert "OpenAI API key is required" in str(exc_info.value)


def test_openai_creates_correct_llm(openai_settings: Settings):
    """OpenAI provider should create ChatOpenAI with correct params."""
    with patch.object(langchain_openai, "ChatOpenAI") as mock_chat_openai:
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm

        result = get_writer_llm(openai_settings)

        assert result == mock_llm
        mock_chat_openai.assert_called_once_with(
            api_key="sk-test-key-12345",
            model="gpt-4o-mini",
            temperature=openai_settings.writer_llm_temperature,
            max_tokens=openai_settings.writer_llm_max_tokens,
            timeout=openai_settings.writer_llm_timeout,
        )


# =============================================================================
# Test Anthropic Provider
# =============================================================================


def test_anthropic_missing_api_key_raises_error():
    """Anthropic provider without API key should raise error."""
    settings = Settings(
        google_api_key="test-google-api",
        google_cse_id="test-cse-id",
        writer_llm_provider="anthropic",
        anthropic_api_key="",
    )

    with pytest.raises(LLMProviderError) as exc_info:
        get_writer_llm(settings)

    assert "Anthropic API key is required" in str(exc_info.value)


def test_anthropic_creates_correct_llm(anthropic_settings: Settings):
    """Anthropic provider should create ChatAnthropic with correct params."""
    with patch.object(langchain_anthropic, "ChatAnthropic") as mock_chat_anthropic:
        mock_llm = MagicMock()
        mock_chat_anthropic.return_value = mock_llm

        result = get_writer_llm(anthropic_settings)

        assert result == mock_llm
        mock_chat_anthropic.assert_called_once_with(
            api_key="sk-ant-test-key-12345",
            model="claude-3-5-sonnet-20241022",
            temperature=anthropic_settings.writer_llm_temperature,
            max_tokens=anthropic_settings.writer_llm_max_tokens,
            timeout=anthropic_settings.writer_llm_timeout,
        )


# =============================================================================
# Test Google Provider
# =============================================================================


def test_google_missing_api_key_raises_error():
    """Google provider without API key should raise error."""
    settings = Settings(
        google_api_key="test-google-api",
        google_cse_id="test-cse-id",
        writer_llm_provider="google",
        google_genai_api_key="",
    )

    with pytest.raises(LLMProviderError) as exc_info:
        get_writer_llm(settings)

    assert "Google Generative AI API key is required" in str(exc_info.value)


def test_google_creates_correct_llm(google_settings: Settings):
    """Google provider should create ChatGoogleGenerativeAI with correct params."""
    with patch.object(langchain_google_genai, "ChatGoogleGenerativeAI") as mock_chat_google:
        mock_llm = MagicMock()
        mock_chat_google.return_value = mock_llm

        result = get_writer_llm(google_settings)

        assert result == mock_llm
        mock_chat_google.assert_called_once_with(
            google_api_key="test-genai-key",
            model="gemini-1.5-flash",
            temperature=google_settings.writer_llm_temperature,
            max_output_tokens=google_settings.writer_llm_max_tokens,
        )


# =============================================================================
# Test Local Provider
# =============================================================================


def test_local_creates_correct_llm(local_settings: Settings):
    """Local provider should create ChatOpenAI with base_url for local server."""
    with patch.object(langchain_openai, "ChatOpenAI") as mock_chat_openai:
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm

        result = get_writer_llm(local_settings)

        assert result == mock_llm
        mock_chat_openai.assert_called_once_with(
            base_url="http://127.0.0.1:1234/v1",
            api_key="not-needed",
            model="local-model",
            temperature=local_settings.writer_llm_temperature,
            max_tokens=local_settings.writer_llm_max_tokens,
            timeout=local_settings.writer_llm_timeout,
        )


# =============================================================================
# Test Health Check
# =============================================================================


@patch("src.check_it_ai.llm.providers.get_writer_llm")
def test_health_check_returns_healthy(mock_get_llm: MagicMock, local_settings: Settings):
    """Health check should return healthy status when LLM can be created."""
    mock_get_llm.return_value = MagicMock()

    result = check_provider_health(local_settings)

    assert result["healthy"] is True
    assert result["provider"] == "local"
    assert result["model"] == "local-model"


@patch("src.check_it_ai.llm.providers.get_writer_llm")
def test_health_check_returns_unhealthy_on_error(mock_get_llm: MagicMock, base_settings: Settings):
    """Health check should return unhealthy status when LLM creation fails."""
    mock_get_llm.side_effect = LLMProviderError("Test error")

    result = check_provider_health(base_settings)

    assert result["healthy"] is False
    assert "error" in result
    assert "Test error" in result["error"]


# =============================================================================
# Test Configuration Defaults
# =============================================================================


def test_default_provider_is_local():
    """Default provider should be 'local' for demo/presentation use."""
    settings = Settings(
        google_api_key="test",
        google_cse_id="test",
    )
    assert settings.writer_llm_provider == "local"


def test_default_local_url_is_lm_studio():
    """Default local URL should be LM Studio's default port."""
    settings = Settings(
        google_api_key="test",
        google_cse_id="test",
    )
    assert settings.local_llm_base_url == "http://127.0.0.1:1234/v1"


def test_default_temperature_is_balanced():
    """Default temperature should be 0.3 for balanced output."""
    settings = Settings(
        google_api_key="test",
        google_cse_id="test",
    )
    assert settings.writer_llm_temperature == 0.3
