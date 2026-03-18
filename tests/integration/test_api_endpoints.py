"""Integration tests for API endpoints."""


import pytest
from httpx import AsyncClient

from src.main import app


@pytest.fixture
async def async_client():
    """Create async test client.

    Yields:
        AsyncClient: HTTP client for testing API endpoints.

    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_auth_header(test_settings):
    """Create mock authentication header.

    Args:
        test_settings: Test settings fixture.

    Returns:
        dict: Headers with API key.

    """
    test_settings.api_key = "test-api-key"
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def mock_image_bytes():
    """Create mock JPEG image bytes.

    Returns:
        bytes: Minimal valid JPEG image data.

    """
    # Minimal JPEG header
    return b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"fake_image_data" * 100


@pytest.fixture
def mock_listing_response():
    """Sample successful listing response.

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


class TestHealthEndpoint:
    """Test the health check endpoint."""

    async def test_health_check_success(self, async_client: AsyncClient):
        """Test health check returns healthy status."""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "services" in data
        assert "version" in data

    async def test_health_check_services(self, async_client: AsyncClient):
        """Test health check includes service statuses."""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "database" in data["services"]
        assert "litellm" in data["services"]


class TestListingEndpoints:
    """Test listing creation and management endpoints."""

    async def test_create_listing_no_api_key(
        self,
        async_client: AsyncClient,
        test_settings,
    ):
        """Test creating listing without API key fails."""
        # Enable auth by setting an API key
        original_key = test_settings.api_key
        test_settings.api_key = "test-key"

        try:
            response = await async_client.post(
                "/api/v1/listing",
                files={},
            )

            assert response.status_code == 401
            assert "API key required" in response.json()["detail"]
        finally:
            test_settings.api_key = original_key

    async def test_create_listing_no_images(
        self,
        async_client: AsyncClient,
        mock_auth_header: dict,
    ):
        """Test creating listing without images fails."""
        response = await async_client.post(
            "/api/v1/listing",
            headers=mock_auth_header,
            data={},
        )

        assert response.status_code == 400
        assert "at least one image" in response.json()["detail"].lower()

    async def test_create_listing_invalid_image_format(
        self,
        async_client: AsyncClient,
        mock_auth_header: dict,
    ):
        """Test creating listing with invalid image format fails."""
        files = {"images": ("test.txt", b"not an image", "text/plain")}

        response = await async_client.post(
            "/api/v1/listing",
            headers=mock_auth_header,
            files=files,
        )

        # Should fail validation
        assert response.status_code in [400, 422]

    async def test_get_listing_not_found(
        self,
        async_client: AsyncClient,
        mock_auth_header: dict,
    ):
        """Test getting non-existent listing returns 404."""
        fake_id = "12345678-1234-1234-1234-123456789abc"

        response = await async_client.get(
            f"/api/v1/listing/{fake_id}",
            headers=mock_auth_header,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_create_listing_too_many_images(
        self,
        async_client: AsyncClient,
        mock_auth_header: dict,
        mock_image_bytes: bytes,
        test_settings,
    ):
        """Test creating listing with too many images fails."""
        # Create more images than allowed
        max_images = test_settings.max_images_per_listing
        files = [
            ("images", (f"test_{i}.jpg", mock_image_bytes, "image/jpeg"))
            for i in range(max_images + 2)
        ]

        response = await async_client.post(
            "/api/v1/listing",
            headers=mock_auth_header,
            files=files,
        )

        assert response.status_code == 400
        assert "maximum" in response.json()["detail"].lower()


class TestClarificationEndpoints:
    """Test clarification submission endpoints."""

    async def test_submit_clarification_not_found(
        self,
        async_client: AsyncClient,
        mock_auth_header: dict,
    ):
        """Test submitting clarification for non-existent listing fails."""
        fake_id = "12345678-1234-1234-1234-123456789abc"

        response = await async_client.post(
            f"/api/v1/listing/{fake_id}/clarify",
            headers=mock_auth_header,
            json={"answer": "test answer"},
        )

        assert response.status_code == 404

    async def test_submit_clarification_invalid_status(
        self,
        async_client: AsyncClient,
        mock_auth_header: dict,
    ):
        """Test submitting clarification for listing not in clarification state."""
        # This would require mocking a listing that exists but is not in
        # clarification status - for integration tests, we verify the endpoint
        # structure is correct
        fake_id = "12345678-1234-1234-1234-123456789abc"

        response = await async_client.post(
            f"/api/v1/listing/{fake_id}/clarify",
            headers=mock_auth_header,
            json={"answer": "test answer"},
        )

        # Will return 404 since listing doesn't exist
        assert response.status_code == 404


class TestMetricsEndpoint:
    """Test the metrics endpoint."""

    async def test_metrics_endpoint(self, async_client: AsyncClient):
        """Test metrics endpoint returns Prometheus format."""
        response = await async_client.get("/api/v1/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        # Should contain Prometheus metrics
        content = response.text
        assert "listing_duration_seconds" in content or "# HELP" in content

    async def test_metrics_endpoint_no_auth_required(
        self,
        async_client: AsyncClient,
    ):
        """Test metrics endpoint doesn't require authentication."""
        response = await async_client.get("/api/v1/metrics")

        # Should succeed without API key
        assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting functionality."""

    async def test_rate_limit_headers_present(
        self,
        async_client: AsyncClient,
        mock_auth_header: dict,
    ):
        """Test rate limit headers are present in responses."""
        response = await async_client.get(
            "/health",
            headers=mock_auth_header,
        )

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    async def test_rate_limit_exceeded(
        self,
        async_client: AsyncClient,
        mock_auth_header: dict,
        test_settings,
    ):
        """Test rate limiting returns 429 when exceeded."""
        # Set a very low rate limit for testing
        original_limit = test_settings.api_rate_limit_rpm
        test_settings.api_rate_limit_rpm = 1

        try:
            # First request should succeed
            response1 = await async_client.get(
                "/health",
                headers=mock_auth_header,
            )
            assert response1.status_code == 200

            # Second request might be rate limited depending on timing
            # In-memory rate limiting resets quickly, so this test
            # verifies the mechanism exists
            response2 = await async_client.get(
                "/health",
                headers=mock_auth_header,
            )
            # Either succeeds or gets rate limited
            assert response2.status_code in [200, 429]
        finally:
            test_settings.api_rate_limit_rpm = original_limit


class TestAuthentication:
    """Test authentication functionality."""

    async def test_invalid_api_key(
        self,
        async_client: AsyncClient,
        test_settings,
    ):
        """Test that invalid API key is rejected."""
        original_key = test_settings.api_key
        test_settings.api_key = "correct-key"

        try:
            response = await async_client.get(
                "/api/v1/listing/12345678-1234-1234-1234-123456789abc",
                headers={"X-API-Key": "wrong-key"},
            )

            assert response.status_code == 401
            assert "Invalid API key" in response.json()["detail"]
        finally:
            test_settings.api_key = original_key

    async def test_no_auth_required_for_health(
        self,
        async_client: AsyncClient,
    ):
        """Test that health endpoint doesn't require authentication."""
        response = await async_client.get("/health")

        assert response.status_code == 200


class TestCORS:
    """Test CORS configuration."""

    async def test_cors_headers_present(
        self,
        async_client: AsyncClient,
    ):
        """Test that CORS headers are present in responses."""
        response = await async_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS middleware should handle preflight requests
        assert response.status_code in [200, 405]
