"""FastAPI application entry point with structured logging."""

import logging
import os
import re
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from structlog.contextvars import bind_contextvars, clear_contextvars

from src.api.middleware import setup_middleware
from src.api.routes import router
from src.config import get_settings
from src.db.session import init_db

# PII patterns to redact
PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}"),
    "ssn": re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "address": re.compile(
        r"\d+\s+[a-zA-Z\s,]+(?:street|st|avenue|ave|road|rd|lane|ln|drive|dr|boulevard|blvd)\b",
        re.IGNORECASE,
    ),
}

# Sensitive field names to redact
SENSITIVE_FIELDS = {
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "credit_card",
    "creditcard",
    "ssn",
    "address",
    "phone",
    "email",
}


def redact_pii(value: Any, _key: str) -> Any:
    """Redact PII from log values.

    Args:
        value: The value to potentially redact.
        _key: The key associated with the value (unused).

    Returns:
        The value with PII redacted or [REDACTED] for sensitive fields.

    """
    if not isinstance(value, str):
        return value

    # Check if the key is a sensitive field name
    lower_key = _key.lower()
    if lower_key in SENSITIVE_FIELDS:
        return "[REDACTED]"

    # Redact PII patterns from string values
    redacted = value
    for pattern in PII_PATTERNS.values():
        redacted = pattern.sub("[REDACTED]", redacted)

    return redacted


def pii_redaction_processor(
    _logger: logging.Logger,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor to redact PII from log entries.

    Args:
        logger: The logger instance.
        method_name: The log method name.
        event_dict: The event dictionary to process.

    Returns:
        The event dictionary with PII redacted.

    """
    redacted: dict[str, Any] = {}
    for key, value in event_dict.items():
        redacted[key] = redact_pii(value, key)
    return redacted


def configure_structlog() -> None:
    """Configure structlog with appropriate processors."""
    # Detect environment - default to development
    environment = os.getenv("MARKETPLACE_ENVIRONMENT", "development")
    is_production = environment.lower() in ("production", "prod")

    # Build processors list
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        pii_redaction_processor,
    ]

    # Use JSON renderer in production, console in development
    if is_production:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Configure structlog on module import
configure_structlog()

# Module-level logger
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    logger.info(
        "application_startup",
        version="0.1.0",
        api_host=settings.api_host,
        api_port=settings.api_port,
    )
    await init_db()
    logger.info("database_initialized")
    yield
    # Shutdown
    logger.info("application_shutdown")


app = FastAPI(
    title="Marketplace Listing Agent",
    description="AI agent for generating eBay and Vinted listings",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def context_injection_middleware(
    request: Request,
    call_next: Any,
) -> Response:
    """Middleware to inject context variables for structured logging.

    Binds listing_id, request_id, and node_name to the logging context
    for each request.

    Args:
        request: The incoming HTTP request.
        call_next: The next middleware or route handler.

    Returns:
        The HTTP response.

    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())

    # Extract listing_id from path if present
    listing_id: str | None = None
    path_parts = request.url.path.split("/")
    if "listings" in path_parts:
        listings_idx = path_parts.index("listings")
        if len(path_parts) > listings_idx + 1:
            listing_id = path_parts[listings_idx + 1]

    # Determine node name from request path
    node_name = request.url.path.strip("/").replace("/", "_") or "root"

    # Bind context variables
    bind_contextvars(request_id=request_id)
    if listing_id:
        bind_contextvars(listing_id=listing_id)
    bind_contextvars(node_name=node_name)

    logger.debug(
        "request_started",
        method=request.method,
        path=request.url.path,
        query_params=dict(request.query_params),
    )

    try:
        response = await call_next(request)
        logger.debug(
            "request_completed",
            status_code=response.status_code,
        )
        return response
    finally:
        # Clear context variables after request
        clear_contextvars()


# Setup all middleware (CORS, rate limiting, metrics, compression)
setup_middleware(app)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/health", include_in_schema=False)
async def health_check_redirect() -> Response:
    """Shallow health check for Docker / load-balancer probes.

    Returns:
        Plain 200 OK so Docker healthcheck passes quickly.
        For the full service-level health check use GET /api/v1/health.

    """
    return Response(content='{"status":"ok"}', media_type="application/json")
