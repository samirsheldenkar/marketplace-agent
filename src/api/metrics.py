"""Prometheus metrics for marketplace listing agent."""

import time
from collections.abc import Generator
from contextlib import contextmanager

from prometheus_client import Counter, Histogram

# Histograms
LISTING_DURATION = Histogram(
    "listing_duration_seconds",
    "Time to generate a complete listing",
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)

SCRAPER_DURATION = Histogram(
    "scraper_duration_seconds",
    "Time for scraper operations",
    ["source"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

LLM_DURATION = Histogram(
    "llm_duration_seconds",
    "Time for LLM calls",
    ["model_type"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

# Counters
SCRAPER_ERRORS = Counter(
    "scraper_error_total",
    "Total scraper errors",
    ["source"],
)

LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Total tokens used",
    ["model_type"],
)

LLM_COST_USD = Counter(
    "llm_cost_usd_total",
    "Total LLM cost in USD",
)

LISTINGS_TOTAL = Counter(
    "listings_total",
    "Total listings created",
    ["status"],
)

CLARIFICATION_ROUNDS = Counter(
    "clarification_rounds_total",
    "Total clarification rounds",
)

REQUESTS_TOTAL = Counter(
    "requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)


# Context managers for timing operations
@contextmanager
def timed_listing_creation() -> Generator[None, None, None]:
    """Context manager to time listing creation."""
    start = time.time()
    yield
    duration = time.time() - start
    LISTING_DURATION.observe(duration)


@contextmanager
def timed_scraper(source: str) -> Generator[None, None, None]:
    """Context manager to time scraper operations.

    Args:
        source: The scraper source ("ebay" or "vinted")

    """
    start = time.time()
    yield
    duration = time.time() - start
    SCRAPER_DURATION.labels(source=source).observe(duration)


@contextmanager
def timed_llm(model_type: str) -> Generator[None, None, None]:
    """Context manager to time LLM calls.

    Args:
        model_type: The model type ("vision", "reasoning", or "drafting")

    """
    start = time.time()
    yield
    duration = time.time() - start
    LLM_DURATION.labels(model_type=model_type).observe(duration)


# Helper functions for recording metrics
def record_scraper_error(source: str) -> None:
    """Record a scraper error.

    Args:
        source: The scraper source ("ebay" or "vinted")

    """
    SCRAPER_ERRORS.labels(source=source).inc()


def record_llm_tokens(model_type: str, tokens: int) -> None:
    """Record LLM token usage.

    Args:
        model_type: The model type ("vision", "reasoning", or "drafting")
        tokens: Number of tokens used

    """
    LLM_TOKENS.labels(model_type=model_type).inc(tokens)


def record_llm_cost(cost_usd: float) -> None:
    """Record LLM cost in USD.

    Args:
        cost_usd: Cost in USD

    """
    LLM_COST_USD.inc(cost_usd)


def record_listing_status(status: str) -> None:
    """Record listing creation status.

    Args:
        status: The listing status ("completed", "clarification", or "failed")

    """
    LISTINGS_TOTAL.labels(status=status).inc()


def record_clarification_round() -> None:
    """Record a clarification round."""
    CLARIFICATION_ROUNDS.inc()


def record_request(method: str, endpoint: str, status: int) -> None:
    """Record an HTTP request.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: Request endpoint path
        status: HTTP status code

    """
    REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=str(status)).inc()
