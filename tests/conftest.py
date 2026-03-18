"""Pytest configuration and shared fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import UploadFile
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import Settings
from src.main import app
from src.models.database import Base
from src.models.state import ListState

# Test database URL (SQLite in-memory for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Test settings fixture.

    Returns:
        Settings: Test configuration with safe defaults.

    """
    return Settings(
        database_url=TEST_DATABASE_URL,
        api_key="test-api-key",
        image_storage_path="/tmp/test_images",
        litellm_url="http://localhost:4000",
        litellm_api_key="test-litellm-key",
        vision_model="openai/gpt-4o",
        reasoning_model="openai/gpt-4o",
        drafting_model="ollama/llama3",
        confidence_threshold=0.7,
        price_discount_pct=10.0,
        max_scraper_results=50,
        scraper_timeout_seconds=30,
        max_image_size_mb=10,
        max_images_per_listing=10,
        allowed_image_formats=["jpg", "jpeg", "png", "webp", "gif"],
        max_tokens_per_listing=8000,
        max_llm_cost_per_listing_usd=0.50,
        apify_api_token="test-apify-token",
        apify_ebay_actor_id="caffein.dev/ebay-sold-listings",
        ebay_country="GB",
        vinted_country="GB",
        api_host="0.0.0.0",
        api_port=8000,
        api_rate_limit_rpm=30,
        redis_url="",
    )


@pytest.fixture
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine for tests.

    Yields:
        AsyncEngine: SQLAlchemy async engine with in-memory SQLite.

    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine) -> AsyncSession:
    """Create database session for tests.

    Creates all tables, yields a session, and rolls back after test.

    Args:
        async_engine: The async engine fixture.

    Yields:
        AsyncSession: Database session for testing.

    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_image_file() -> UploadFile:
    """Create a mock image file for testing.

    Returns:
        UploadFile: Mock FastAPI upload file with test content.

    """
    content = b"fake image content for testing"
    file = BytesIO(content)
    return UploadFile(
        filename="test.jpg",
        file=file,
    )


@pytest.fixture
def mock_image_files() -> list[UploadFile]:
    """Create multiple mock image files for testing.

    Returns:
        list[UploadFile]: List of mock upload files.

    """
    files = []
    for i in range(3):
        content = f"fake image content {i}".encode()
        file = BytesIO(content)
        files.append(
            UploadFile(
                filename=f"test_{i}.jpg",
                file=file,
            )
        )
    return files


@pytest.fixture
def sample_listing_data() -> dict[str, Any]:
    """Sample listing data for tests.

    Returns:
        dict: Sample listing data dictionary.

    """
    return {
        "item_type": "headphones",
        "brand": "Sony",
        "model_name": "WH-1000XM5",
        "condition": "Good",
        "confidence": 0.91,
        "item_description": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        "color": "Black",
        "size": None,
        "condition_notes": "Minor scratches on headband",
        "accessories_included": ["carrying case", "charging cable"],
    }


@pytest.fixture
def sample_state() -> ListState:
    """Sample agent state for tests.

    Returns:
        ListState: Complete agent state for testing.

    """
    return ListState(
        run_id="test-run-id-123",
        messages=[],
        photos=["/tmp/test_images/test_0.jpg", "/tmp/test_images/test_1.jpg"],
        item_description="Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        item_type="headphones",
        brand="Sony",
        model_name="WH-1000XM5",
        size=None,
        color="Black",
        condition="Good",
        condition_notes="Minor scratches on headband",
        confidence=0.91,
        accessories_included=["carrying case", "charging cable"],
        image_analysis_raw={
            "detected_items": ["headphones"],
            "brand_detected": "Sony",
            "condition_assessment": "Good",
        },
        ebay_price_stats={
            "num_listings": 25,
            "avg_price": 180.50,
            "median_price": 175.00,
            "min_price": 120.00,
            "max_price": 250.00,
            "items": [],
        },
        vinted_price_stats={
            "num_listings": 15,
            "avg_price": 165.00,
            "median_price": 160.00,
            "min_price": 100.00,
            "max_price": 220.00,
            "items": [],
        },
        ebay_query_used="Sony WH-1000XM5 headphones",
        vinted_query_used="Sony WH-1000XM5",
        suggested_price=150.0,
        preferred_platform="ebay",
        platform_reasoning="Higher average price on eBay with more listings",
        fast_sale=False,
        listing_draft={
            "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones - Black - Good Condition",
            "description": "Excellent Sony WH-1000XM5 headphones in good condition.",
            "category_suggestions": ["Electronics > Headphones", "Audio > Headphones"],
            "shipping_suggestion": "Standard shipping recommended",
            "returns_policy": "30-day returns accepted",
            "platform_variants": {},
        },
        needs_clarification=False,
        clarification_question=None,
        error_state=None,
        retry_count=0,
    )


@pytest.fixture
def sample_state_needs_clarification() -> ListState:
    """Sample agent state that needs clarification.

    Returns:
        ListState: Agent state requiring user clarification.

    """
    return ListState(
        run_id="test-run-id-456",
        messages=[],
        photos=["/tmp/test_images/unclear_item.jpg"],
        item_description="Unknown item",
        item_type="unknown",
        brand=None,
        model_name=None,
        size=None,
        color=None,
        condition="Unknown",
        condition_notes=None,
        confidence=0.35,
        accessories_included=[],
        image_analysis_raw=None,
        ebay_price_stats=None,
        vinted_price_stats=None,
        ebay_query_used=None,
        vinted_query_used=None,
        suggested_price=None,
        preferred_platform=None,
        platform_reasoning=None,
        fast_sale=False,
        listing_draft=None,
        needs_clarification=True,
        clarification_question="Could you provide more details about the item? What type of item is this?",
        error_state=None,
        retry_count=0,
    )


@pytest.fixture
def sample_price_stats() -> dict[str, Any]:
    """Sample price statistics for tests.

    Returns:
        dict: Sample price statistics dictionary.

    """
    return {
        "num_listings": 25,
        "avg_price": 180.50,
        "median_price": 175.00,
        "min_price": 120.00,
        "max_price": 250.00,
        "items": [
            {
                "title": "Sony WH-1000XM5 - Excellent",
                "price": 200.00,
                "url": "https://ebay.com/1",
            },
            {
                "title": "Sony WH-1000XM5 - Good",
                "price": 150.00,
                "url": "https://ebay.com/2",
            },
        ],
    }


@pytest.fixture
def sample_listing_draft() -> dict[str, Any]:
    """Sample listing draft for tests.

    Returns:
        dict: Sample listing draft dictionary.

    """
    return {
        "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones - Black - Good Condition",
        "description": (
            "Excellent Sony WH-1000XM5 wireless noise cancelling headphones in good condition.\n\n"
            "Features:\n"
            "- Industry-leading noise cancellation\n"
            "- 30-hour battery life\n"
            "- Multipoint connection\n"
            "- Speak-to-Chat technology\n\n"
            "Condition: Good - Minor scratches on headband, fully functional.\n"
            "Includes: Carrying case, charging cable."
        ),
        "category_suggestions": [
            "Electronics > Headphones > Over-Ear Headphones",
            "Audio > Headphones > Noise Cancelling",
        ],
        "shipping_suggestion": "Royal Mail Tracked 48 recommended for UK buyers",
        "returns_policy": "30-day returns accepted, buyer pays return shipping",
        "platform_variants": {
            "ebay": {
                "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones Black Good",
                "category_id": "15022",
            },
            "vinted": {
                "title": "Sony WH-1000XM5 Casque sans fil",
                "category_id": "1869",
            },
        },
    }


@pytest.fixture
def mock_litellm_client() -> MagicMock:
    """Mock LiteLLM client for testing.

    Returns:
        MagicMock: Mock LiteLLM client.

    """
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"item_type": "headphones", "brand": "Sony", "confidence": 0.91}'
                    )
                )
            ],
            usage=MagicMock(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
            ),
        )
    )
    return client


@pytest.fixture
def mock_scraper_response() -> dict[str, Any]:
    """Mock scraper response for testing.

    Returns:
        dict: Mock scraper response dictionary.

    """
    return {
        "items": [
            {
                "title": "Sony WH-1000XM5 Wireless Headphones - Excellent",
                "price": 199.99,
                "currency": "GBP",
                "condition": "Excellent",
                "url": "https://ebay.com/item/1",
                "image_url": "https://ebay.com/image/1.jpg",
            },
            {
                "title": "Sony WH-1000XM5 Headphones - Good Condition",
                "price": 149.99,
                "currency": "GBP",
                "condition": "Good",
                "url": "https://ebay.com/item/2",
                "image_url": "https://ebay.com/image/2.jpg",
            },
        ],
        "total_count": 25,
        "query_used": "Sony WH-1000XM5",
    }


@pytest.fixture
def temp_image_dir(tmp_path) -> str:
    """Create temporary directory for test images.

    Args:
        tmp_path: pytest tmp_path fixture.

    Returns:
        str: Path to temporary image directory.

    """
    image_dir = tmp_path / "test_images"
    image_dir.mkdir()
    return str(image_dir)


@pytest.fixture
def sample_image_paths(temp_image_dir: str) -> list[str]:
    """Create sample image files for testing.

    Args:
        temp_image_dir: Temporary image directory fixture.

    Returns:
        list[str]: List of paths to sample image files.

    """
    import os

    paths = []
    for i in range(3):
        path = os.path.join(temp_image_dir, f"test_{i}.jpg")
        with open(path, "wb") as f:
            f.write(b"fake image content")
        paths.append(path)
    return paths


# Integration test fixtures


@pytest.fixture
async def async_client():
    """Create async test client for integration tests.

    Yields:
        AsyncClient: HTTP client for testing API endpoints.

    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_auth_header(test_settings):
    """Create mock authentication header for integration tests.

    Args:
        test_settings: Test settings fixture.

    Returns:
        dict: Headers with API key.

    """
    test_settings.api_key = "test-api-key"
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def mock_image_bytes():
    """Create mock JPEG image bytes for integration tests.

    Returns:
        bytes: Minimal valid JPEG image data.

    """
    # Minimal JPEG header
    return b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"fake_image_data" * 100


@pytest.fixture
def mock_listing_response():
    """Sample successful listing response for integration tests.

    Returns:
        dict: Sample listing response data.

    """
    return {
        "listing_id": "test-uuid",
        "status": "completed",
        "item": {
            "type": "headphones",
            "brand": "Sony",
            "model": "WH-1000XM5",
            "condition": "Good",
            "confidence": 0.91,
        },
        "pricing": {
            "suggested_price": 142.00,
            "currency": "GBP",
            "preferred_platform": "ebay",
            "platform_reasoning": "Higher volume on eBay",
        },
        "listing_draft": {
            "title": "Sony WH-1000XM5 Headphones - Good Condition",
            "description": "High-quality noise-canceling headphones...",
            "category_suggestions": ["Sound & Vision > Headphones"],
            "shipping_suggestion": "Royal Mail 2nd Class",
            "returns_policy": "30-day returns",
        },
    }
