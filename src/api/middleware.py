"""FastAPI middleware configuration."""

import time

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import get_settings


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request timing."""

    async def dispatch(self, request: Request, call_next):
        """Process request and log timing."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


def setup_middleware(app):
    """Configure all middleware for the FastAPI app.

    Args:
        app: FastAPI application instance
    """
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

    # Request timing
    app.add_middleware(RequestTimingMiddleware)
