"""Configuration module using pydantic-settings for type-safe env variable loading."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

AgentRoute = Literal["fact_check", "clarify", "out_of_scope"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Uses pydantic-settings for type-safe configuration with validation.
    Automatically loads from .env file if present.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Google Custom Search API Configuration
    google_api_key: str = Field(
        default="",
        description="Google Custom Search JSON API key",
    )
    google_cse_id: str = Field(
        default="",
        description="Google Custom Search Engine ID (Programmable Search Engine)",
    )

    # Search Engine Fallback Configuration
    use_duckduckgo_backup: bool = Field(
        default=False,
        description="Enable DuckDuckGo fallback when Google quota is exceeded",
    )
    use_fact_check_api: bool = Field(
        default=True,
        description="Enable Google Fact Check Tools API for professional fact-checks",
    )

    # Application Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # Directory Configuration
    cache_dir: Path = Field(
        default=Path("./cache"),
        description="Directory for caching search results",
    )
    model_dir: Path = Field(
        default=Path("./models"),
        description="Directory for storing model files and LoRA adapters",
    )

    # Search Configuration
    max_search_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of search results to retrieve per query",
    )
    search_timeout: int = Field(
        default=30,
        ge=1,
        le=120,
        description="Timeout in seconds for search API requests",
    )

    # Cache Configuration
    cache_ttl_hours: int = Field(
        default=24,
        ge=1,
        description="Time-to-live for cached search results in hours",
    )
    router_debug: bool = True  # controls extra logging & UI debug panel
    offline_mode: bool = False  # optional, for researcher/offline demos
    trusted_domains_only: bool = False  # optional, for researcher's site: filters

    # API Server Configuration
    use_mock: bool = Field(
        default=False,
        description="Use mock service instead of real run_graph for UI development",
    )

    # Router Configuration (Phase 3: AH-05)
    router_current_events_years_ago: int = Field(
        default=2,
        ge=0,
        le=10,
        description=(
            "How many years back to consider 'current events' (out of scope). "
            "Set to 0 to allow all recent events. "
            "Default: 2 (events from last 2 years rejected)"
        ),
    )
    router_min_query_words: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Minimum words required for valid query (used for underspecified detection)",
    )
    router_min_query_chars: int = Field(
        default=8,
        ge=1,
        le=100,
        description="Minimum characters required for valid query (used for underspecified detection)",
    )

    # Language Configuration
    default_language: str = Field(
        default="en",
        description="Default language code (ISO 639-1) for fact-check searches (e.g., 'en', 'he', 'ar', 'es')",
    )
    fallback_language: str = Field(
        default="en",
        description="Fallback language code when no results found in default language",
    )

    # =========================================================================
    # Writer LLM Configuration
    # =========================================================================
    writer_llm_provider: Literal["openai", "anthropic", "google", "local"] = Field(
        default="local",
        description="LLM provider for writer node: openai, anthropic, google, or local",
    )
    analyst_llm_provider: Literal["openai", "anthropic", "google", "local"] = Field(
        default="local",
        description="LLM provider for writer node: openai, anthropic, google, or local",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key (required if writer_llm_provider='openai')",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model name (e.g., 'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo')",
    )

    # Anthropic Configuration
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key (required if writer_llm_provider='anthropic')",
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Anthropic model name (e.g., 'claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307')",
    )

    # Google Generative AI Configuration
    google_genai_api_key: str = Field(
        default="",
        description="Google Generative AI API key (required if writer_llm_provider='google')",
    )
    google_genai_model: str = Field(
        default="gemini-1.5-flash",
        description="Google Generative AI model name (e.g., 'gemini-1.5-pro', 'gemini-1.5-flash')",
    )

    # Local LLM Configuration (LM Studio / Ollama / vLLM)
    local_llm_base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        description="Base URL for local OpenAI-compatible API (LM Studio, Ollama, vLLM)",
    )
    local_llm_model: str = Field(
        default="local-model",
        description="Model name for local LLM (depends on your local server setup)",
    )
    local_llm_api_key: str = Field(
        default="not-needed",
        description="API key for local LLM (usually 'not-needed' for local servers)",
    )

    # Common LLM Settings
    writer_llm_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Temperature for writer LLM (0.0=deterministic, higher=creative)",
    )
    writer_llm_max_tokens: int = Field(
        default=1024,
        ge=100,
        le=8192,
        description="Maximum tokens for writer LLM response",
    )
    writer_llm_timeout: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Timeout in seconds for writer LLM API calls",
    )

    # =========================================================================
    # Analyst LLM Configuration
    # =========================================================================
    analyst_llm_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Temperature for analyst LLM (low for factual tasks)",
    )
    analyst_llm_max_tokens: int = Field(
        default=512,
        ge=100,
        le=2048,
        description="Maximum tokens for analyst LLM response",
    )
    analyst_llm_timeout: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Timeout in seconds for writer LLM API calls",
    )

    def __init__(self, **kwargs):
        """Initialize settings and create necessary directories."""
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
