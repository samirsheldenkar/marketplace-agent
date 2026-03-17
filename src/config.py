"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings use the MARKETPLACE_ prefix for environment variables.
    Configuration can be loaded from a .env file in the project root.

    Attributes:
        database_url: PostgreSQL connection string.
        pool_size: Database connection pool size.
        max_overflow: Maximum overflow connections for the pool.
        litellm_url: LiteLLM gateway URL.
        litellm_api_key: API key for LiteLLM authentication.
        vision_model: Model for image analysis tasks.
        reasoning_model: Model for reasoning/analysis tasks.
        drafting_model: Model for content drafting tasks.
        confidence_threshold: Minimum confidence for item classification.
        price_discount_pct: Default price discount percentage.
        max_scraper_results: Maximum results from scrapers.
        scraper_timeout_seconds: Timeout for scraper operations.
        max_image_size_mb: Maximum image file size in megabytes.
        max_images_per_listing: Maximum images per listing.
        allowed_image_formats: Supported image formats.
        image_storage_path: Path for storing uploaded images.
        max_tokens_per_listing: Maximum tokens per listing generation.
        max_llm_cost_per_listing_usd: Maximum LLM cost per listing in USD.
        apify_api_token: Apify API token for scrapers.
        apify_ebay_actor_id: Apify actor ID for eBay scraper.
        ebay_country: eBay marketplace country code.
        vinted_country: Vinted marketplace country code.
        api_host: API server host.
        api_port: API server port.
        api_key: API key for authentication.
        api_rate_limit_rpm: Rate limit in requests per minute.
    """

    model_config = SettingsConfigDict(
        env_prefix="MARKETPLACE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database settings
    database_url: str = "postgresql://localhost:5432/marketplace"
    pool_size: int = 5
    max_overflow: int = 10

    # LiteLLM settings
    litellm_url: str = "http://localhost:4000"
    litellm_api_key: str = ""

    # Model routing
    vision_model: str = "gpt-4-vision-preview"
    reasoning_model: str = "gpt-4"
    drafting_model: str = "gpt-3.5-turbo"

    # Agent thresholds
    confidence_threshold: float = 0.7
    price_discount_pct: float = 10.0
    max_scraper_results: int = 50
    scraper_timeout_seconds: int = 30

    # Image handling
    max_image_size_mb: int = 10
    max_images_per_listing: int = 10
    allowed_image_formats: List[str] = ["jpg", "jpeg", "png", "webp", "gif"]
    image_storage_path: str = "/tmp/marketplace_images"

    # Cost controls
    max_tokens_per_listing: int = 8000
    max_llm_cost_per_listing_usd: float = 0.50

    # Scraper config
    apify_api_token: str = ""
    apify_ebay_actor_id: str = "apify/ebay-scraper"
    ebay_country: str = "GB"
    vinted_country: str = "GB"

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = ""
    api_rate_limit_rpm: int = 30


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    This function returns a cached Settings instance, ensuring that
    environment variables are only parsed once during the application
    lifecycle.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()
