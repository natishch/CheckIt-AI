"""Configuration module using pydantic-settings for type-safe env variable loading."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Language Configuration
    default_language: str = Field(
        default="en",
        description="Default language code (ISO 639-1) for fact-check searches (e.g., 'en', 'he', 'ar', 'es')",
    )
    fallback_language: str = Field(
        default="en",
        description="Fallback language code when no results found in default language",
    )

    def __init__(self, **kwargs):
        """Initialize settings and create necessary directories."""
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
