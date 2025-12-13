"""LLM Provider Factory for Writer and Analyst Nodes.

This module provides factory functions to instantiate the appropriate LLM
based on configuration. Supports OpenAI, Anthropic, Google, and local
(LM Studio/Ollama/vLLM) providers.

Usage:
    from src.check_it_ai.llm.providers import get_writer_llm, get_analyst_llm
    from src.check_it_ai.config import settings

    writer_llm = get_writer_llm(settings)
    analyst_llm = get_analyst_llm(settings)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.language_models import BaseChatModel

if TYPE_CHECKING:
    from src.check_it_ai.config import Settings


class LLMProviderError(Exception):
    """Raised when LLM provider configuration is invalid or unavailable."""

    pass


def get_writer_llm(settings: Settings) -> BaseChatModel:
    """Create and return the LLM instance for the Writer node.

    Args:
        settings: Application settings containing LLM configuration.

    Returns:
        A LangChain BaseChatModel instance configured for the writer node.

    Raises:
        LLMProviderError: If the provider is unknown or required API key is missing.
        ImportError: If required provider package is not installed.
    """
    return _get_llm(
        settings,
        provider=settings.writer_llm_provider,
        temperature=settings.writer_llm_temperature,
        max_tokens=settings.writer_llm_max_tokens,
        timeout=settings.writer_llm_timeout,
    )


def get_analyst_llm(settings: Settings) -> BaseChatModel:
    """Create and return the LLM instance for the Fact Analyst node.

    Uses the same provider as writer but with analyst-specific temperature
    and max_tokens settings (lower temperature for factual tasks).

    Args:
        settings: Application settings containing LLM configuration.

    Returns:
        A LangChain BaseChatModel instance configured for the analyst node.

    Raises:
        LLMProviderError: If the provider is unknown or required API key is missing.
        ImportError: If required provider package is not installed.
    """
    return _get_llm(
        settings,
        provider=settings.analyst_llm_provider,
        temperature=settings.analyst_llm_temperature,
        max_tokens=settings.analyst_llm_max_tokens,
        timeout=settings.analyst_llm_timeout,
    )


def _get_llm(settings: Settings, provider: str, **kwargs) -> BaseChatModel:
    """Internal factory that creates the LLM for the specified node type."""

    match provider:
        case "openai":
            return _create_openai_llm(settings, **kwargs)
        case "anthropic":
            return _create_anthropic_llm(settings, **kwargs)
        case "google":
            return _create_google_llm(settings, **kwargs)
        case "local":
            return _create_local_llm(settings, **kwargs)
        case _:
            raise LLMProviderError(
                f"Unknown LLM provider: '{provider}'. "
                f"Supported providers: openai, anthropic, google, local"
            )


def _create_openai_llm(
    settings: Settings,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> BaseChatModel:
    """Create OpenAI ChatGPT instance."""
    if not settings.openai_api_key:
        raise LLMProviderError(
            "OpenAI API key is required when writer_llm_provider='openai'. "
            "Set OPENAI_API_KEY in your .env file."
        )

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        raise ImportError(
            "langchain-openai package is required for OpenAI provider. "
            "Install it with: pip install langchain-openai"
        ) from e

    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def _create_anthropic_llm(
    settings: Settings,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> BaseChatModel:
    """Create Anthropic Claude instance."""
    if not settings.anthropic_api_key:
        raise LLMProviderError(
            "Anthropic API key is required when writer_llm_provider='anthropic'. "
            "Set ANTHROPIC_API_KEY in your .env file."
        )

    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as e:
        raise ImportError(
            "langchain-anthropic package is required for Anthropic provider. "
            "Install it with: pip install langchain-anthropic"
        ) from e

    return ChatAnthropic(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def _create_google_llm(
    settings: Settings,
    temperature: float,
    max_tokens: int,
    timeout: int,  # noqa: ARG001 - Google API doesn't use timeout but kept for interface consistency
) -> BaseChatModel:
    """Create Google Generative AI (Gemini) instance."""
    if not settings.google_genai_api_key:
        raise LLMProviderError(
            "Google Generative AI API key is required when writer_llm_provider='google'. "
            "Set GOOGLE_GENAI_API_KEY in your .env file."
        )

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as e:
        raise ImportError(
            "langchain-google-genai package is required for Google provider. "
            "Install it with: pip install langchain-google-genai"
        ) from e

    return ChatGoogleGenerativeAI(
        google_api_key=settings.google_genai_api_key,
        model=settings.google_genai_model,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )


def _create_local_llm(
    settings: Settings, temperature: float, max_tokens: int, timeout: int
) -> BaseChatModel:
    """Create local LLM instance (LM Studio / Ollama / vLLM).

    Uses OpenAI-compatible API endpoint, which is supported by:
    - LM Studio (default: http://127.0.0.1:1234/v1)
    - Ollama (with OpenAI compatibility layer)
    - vLLM (with OpenAI compatibility layer)
    - Any other OpenAI-compatible local server
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        raise ImportError(
            "langchain-openai package is required for local provider. "
            "Install it with: pip install langchain-openai"
        ) from e

    return ChatOpenAI(
        base_url=settings.local_llm_base_url,
        api_key=settings.local_llm_api_key,
        model=settings.local_llm_model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def check_provider_health(settings: Settings) -> dict[str, bool | str]:
    """Check if the configured LLM provider is available and working.

    This is useful for health checks and debugging.

    Args:
        settings: Application settings containing LLM configuration.

    Returns:
        Dict with 'healthy' (bool), 'provider' (str), and optionally 'error' (str).
    """
    provider = settings.writer_llm_provider.lower()

    try:
        get_writer_llm(settings)
        # For health check, we just verify the LLM can be instantiated
        return {
            "healthy": True,
            "provider": provider,
            "model": _get_model_name(settings, provider),
        }
    except (LLMProviderError, ImportError) as e:
        return {
            "healthy": False,
            "provider": provider,
            "error": str(e),
        }


def _get_model_name(settings: Settings, provider: str) -> str:
    """Get the model name for the given provider."""
    model_map = {
        "openai": settings.openai_model,
        "anthropic": settings.anthropic_model,
        "google": settings.google_genai_model,
        "local": settings.local_llm_model,
    }
    return model_map.get(provider, "unknown")
