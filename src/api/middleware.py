"""FastAPI middleware configuration."""

import time
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from src.api.metrics import record_request

# Optional Redis support
try:
    import redis.asyncio as aioredis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    aioredis = None  # type: ignore[misc,assignment]


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request timing."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and log timing."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and record metrics."""
        response = await call_next(request)

        # Extract endpoint pattern (remove path parameters for consistent metrics)
        endpoint = request.url.path
        method = request.method
        status = response.status_code

        # Record the request metrics
        record_request(method=method, endpoint=endpoint, status=status)

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window counter algorithm.

    Supports Redis for production (distributed rate limiting) and in-memory
    storage for development. Falls back gracefully if Redis is unavailable.
    """

    def __init__(
        self,
        app: Any,
        redis_client: Optional[Any] = None,
        max_requests: int = 30,
        window_seconds: int = 60,
    ) -> None:
        """Initialize rate limiting middleware.

        Args:
            app: FastAPI application instance.
            redis_client: Optional Redis client for distributed rate limiting.
            max_requests: Maximum requests allowed per window.
            window_seconds: Window duration in seconds.

        """
        super().__init__(app)
        self.redis = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._memory_storage: dict[
            str, tuple[int, float]
        ] = {}  # key -> (count, window_start)

    def _get_client_key(self, request: Request) -> str:
        """Generate rate limit key from API key or client IP.

        Args:
            request: The incoming HTTP request.

        Returns:
            Rate limit key string.

        """
        # Prefer API key from header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"rate_limit:{api_key}"

        # Fall back to client IP
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"rate_limit:{client_ip}"

    async def _get_rate_limit_memory(self, key: str) -> tuple[int, float, int]:
        """Get rate limit state from in-memory storage.

        Args:
            key: Rate limit key.

        Returns:
            Tuple of (current_count, window_start, remaining_seconds).

        """
        current_time = time.time()
        window_start = current_time

        if key in self._memory_storage:
            count, stored_start = self._memory_storage[key]
            # Check if window has expired
            if current_time - stored_start < self.window_seconds:
                window_start = stored_start
                remaining = int(self.window_seconds - (current_time - stored_start))
                return count, window_start, remaining

        # New window
        self._memory_storage[key] = (0, current_time)
        return 0, current_time, self.window_seconds

    async def _increment_memory(self, key: str) -> int:
        """Increment counter in memory storage.

        Args:
            key: Rate limit key.

        Returns:
            New count value.

        """
        current_time = time.time()
        if key in self._memory_storage:
            count, window_start = self._memory_storage[key]
            # Reset if window expired
            if current_time - window_start >= self.window_seconds:
                count = 0
                window_start = current_time
            count += 1
            self._memory_storage[key] = (count, window_start)
            return count
        self._memory_storage[key] = (1, current_time)
        return 1

    async def _get_rate_limit_redis(self, key: str) -> tuple[int, float, int]:
        """Get rate limit state from Redis.

        Args:
            key: Rate limit key.

        Returns:
            Tuple of (current_count, window_start, remaining_seconds).

        """
        if self.redis is None:
            return 0, time.time(), self.window_seconds

        try:
            current_time = time.time()
            # Get current count and TTL
            count = await self.redis.get(key)
            ttl = await self.redis.ttl(key)

            if count is None or ttl < 0:
                # Key doesn't exist or expired
                return 0, current_time, self.window_seconds

            count_val = int(count)
            remaining = max(ttl, 0)
            window_start = current_time - (self.window_seconds - remaining)

            return count_val, window_start, remaining
        except Exception:
            # Fall back to memory on Redis error
            return await self._get_rate_limit_memory(key)

    async def _increment_redis(self, key: str) -> int:
        """Increment counter in Redis.

        Args:
            key: Rate limit key.

        Returns:
            New count value.

        """
        if self.redis is None:
            return await self._increment_memory(key)

        try:
            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.window_seconds)
            results = await pipe.execute()
            return int(results[0])
        except Exception:
            # Fall back to memory on Redis error
            return await self._increment_memory(key)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with rate limiting.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            HTTP response.

        """
        key = self._get_client_key(request)
        current_time = time.time()

        # Get current state
        if self.redis is not None:
            count, window_start, remaining = await self._get_rate_limit_redis(key)
        else:
            count, window_start, remaining = await self._get_rate_limit_memory(key)

        # Check if rate limit exceeded
        if count >= self.max_requests:
            retry_after = remaining
            reset_timestamp = int(window_start + self.window_seconds)

            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded. Try again in {retry_after} seconds."
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_timestamp),
                },
            )

        # Increment counter
        if self.redis is not None:
            new_count = await self._increment_redis(key)
        else:
            new_count = await self._increment_memory(key)

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        remaining_requests = max(0, self.max_requests - new_count)
        reset_timestamp = int(window_start + self.window_seconds)

        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining_requests)
        response.headers["X-RateLimit-Reset"] = str(reset_timestamp)

        return response


def setup_middleware(app: FastAPI, redis_client: Optional[Any] = None) -> None:
    """Configure all middleware for the FastAPI app.

    Args:
        app: FastAPI application instance.
        redis_client: Optional Redis client for rate limiting.

    """
    # Import settings here to avoid circular imports
    from src.config import get_settings

    settings = get_settings()

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Rate limiting (before metrics to track rejected requests)
    app.add_middleware(
        RateLimitMiddleware,
        redis_client=redis_client,
        max_requests=settings.api_rate_limit_rpm,
        window_seconds=60,
    )

    # Metrics collection
    app.add_middleware(MetricsMiddleware)

    # Request timing
    app.add_middleware(RequestTimingMiddleware)
