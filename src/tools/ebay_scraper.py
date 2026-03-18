"""eBay scraper tool for fetching sold listings via Apify.

This module provides functionality to scrape eBay sold listings using
the Apify platform. It handles API communication, retry logic, and
response normalization.
"""

import asyncio
import statistics

import httpx
import structlog

from src.config import get_settings
from src.exceptions import ScraperError
from src.models.state import PriceStats

logger = structlog.get_logger()

# Retry configuration
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2


async def scrape_ebay_sold_listings(  # noqa: C901, PLR0911
    query: str,
    country: str = "GB",
    max_results: int = 50,
) -> PriceStats | None:
    """Scrape eBay sold listings for price statistics.

    Uses the Apify platform to fetch sold listings from eBay and
    calculates price statistics for the results.

    Args:
        query: Search query for eBay listings.
        country: eBay marketplace country code (default: "GB").
        max_results: Maximum number of results to fetch (default: 50).

    Returns:
        PriceStats dictionary with price statistics, or None on failure.

    Raises:
        ScraperError: If the scraper encounters a critical error.

    """
    settings = get_settings()

    if not settings.apify_api_token:
        logger.warning(
            "Apify API token not configured",
            query=query,
            country=country,
        )
        return None

    actor_id = settings.apify_ebay_actor_id
    timeout_seconds = settings.scraper_timeout_seconds

    # Prepare the request payload for Apify actor
    payload = {
        "search": query,
        "country": country,
        "resultsPerPage": max_results,
        "soldItems": True,
    }

    headers = {
        "Authorization": f"Bearer {settings.apify_api_token}",
        "Content-Type": "application/json",
    }

    url = f"https://api.apify.com/v2/acts/{actor_id}/runs"

    logger.info(
        "Starting eBay scraper request",
        query=query,
        country=country,
        max_results=max_results,
        actor_id=actor_id,
    )

    # Execute with retry logic
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

                run_data = response.json()
                run_id = run_data.get("data", {}).get("id")

                if not run_id:
                    logger.error(
                        "No run ID in Apify response",
                        response=run_data,
                    )
                    return None

                logger.info(
                    "Apify actor run started",
                    run_id=run_id,
                    actor_id=actor_id,
                )

                # Wait for the run to complete and fetch results
                items = await _wait_for_results(
                    client=client,
                    run_id=run_id,
                    headers=headers,
                    timeout_seconds=timeout_seconds,
                )

                if items is None:
                    return None

                # Normalize to PriceStats
                price_stats = _normalize_to_price_stats(items, query)

                logger.info(
                    "eBay scraper completed successfully",
                    query=query,
                    num_listings=price_stats["num_listings"],
                    avg_price=price_stats["avg_price"],
                )

                return price_stats

        except httpx.TimeoutException as e:
            logger.warning(
                "eBay scraper request timed out",
                query=query,
                attempt=attempt + 1,
                max_retries=MAX_RETRIES,
                error=str(e),
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                continue
            logger.exception(
                "eBay scraper failed after retries",
                query=query,
            )
            return None

        except httpx.HTTPStatusError as e:
            logger.warning(
                "eBay scraper HTTP error",
                query=query,
                attempt=attempt + 1,
                status_code=e.response.status_code,
                error=str(e),
            )
            if attempt < MAX_RETRIES and _is_retryable_error(e.response.status_code):
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                continue
            logger.exception(
                "eBay scraper failed with HTTP error",
                query=query,
                status_code=e.response.status_code,
            )
            return None

        except httpx.RequestError as e:
            logger.warning(
                "eBay scraper request error",
                query=query,
                attempt=attempt + 1,
                error=str(e),
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                continue
            logger.exception(
                "eBay scraper failed after retries",
                query=query,
            )
            return None

        except Exception as e:
            logger.exception(
                "Unexpected error in eBay scraper",
                query=query,
                error=str(e),
            )
            raise ScraperError(f"Unexpected error scraping eBay: {e}") from e

    return None


async def _wait_for_results(
    client: httpx.AsyncClient,
    run_id: str,
    headers: dict,
    timeout_seconds: int,
) -> list[dict] | None:
    """Wait for Apify actor run to complete and fetch results.

    Polls the Apify API for run status and retrieves the dataset
    when the run completes successfully.

    Args:
        client: httpx async client instance.
        run_id: Apify actor run ID.
        headers: Request headers with authentication.
        timeout_seconds: Maximum time to wait for completion.

    Returns:
        List of item dictionaries, or None on failure.

    """
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}"
    dataset_url = f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items"

    poll_interval = 2  # seconds between status checks
    elapsed = 0

    while elapsed < timeout_seconds:
        try:
            status_response = await client.get(status_url, headers=headers)
            status_response.raise_for_status()
            status_data = status_response.json()

            status = status_data.get("data", {}).get("status", "").upper()

            if status == "SUCCEEDED":
                # Fetch the dataset items
                items_response = await client.get(dataset_url, headers=headers)
                items_response.raise_for_status()
                items = items_response.json()
                return items if isinstance(items, list) else []

            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                logger.error(
                    "Apify actor run failed",
                    run_id=run_id,
                    status=status,
                )
                return None

            # Still running, wait and poll again
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        except httpx.HTTPError as e:
            logger.warning(
                "Error polling Apify run status",
                run_id=run_id,
                error=str(e),
            )
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

    logger.error(
        "Apify actor run timed out waiting for completion",
        run_id=run_id,
        elapsed_seconds=elapsed,
    )
    return None


def _normalize_to_price_stats(items: list[dict], query: str) -> PriceStats:
    """Normalize Apify response items to PriceStats format.

    Extracts prices from the scraped items and calculates
    statistics.

    Args:
        items: List of item dictionaries from Apify response.
        query: Original search query (for logging).

    Returns:
        PriceStats dictionary with calculated statistics.

    """
    prices = []

    for item in items:
        price = _extract_price(item)
        if price is not None and price > 0:
            prices.append(price)

    if not prices:
        logger.warning(
            "No valid prices found in scraped items",
            query=query,
            num_items=len(items),
        )
        return PriceStats(
            num_listings=0,
            avg_price=0.0,
            median_price=0.0,
            min_price=0.0,
            max_price=0.0,
            items=[],
        )

    avg_price = statistics.mean(prices)
    median_price = statistics.median(prices)
    min_price = min(prices)
    max_price = max(prices)

    return PriceStats(
        num_listings=len(prices),
        avg_price=round(avg_price, 2),
        median_price=round(median_price, 2),
        min_price=round(min_price, 2),
        max_price=round(max_price, 2),
        items=items,
    )


def _extract_price(item: dict) -> float | None:
    """Extract price from an Apify item response.

    Handles various price formats that may be returned by the
    eBay scraper actor.

    Args:
        item: Single item dictionary from Apify response.

    Returns:
        Price as float, or None if extraction fails.

    """
    # Try common price field names from Apify eBay scraper
    price_fields = ["price", "soldPrice", "currentPrice", "itemPrice"]

    for field in price_fields:
        if field in item:
            price_value = item[field]
            if isinstance(price_value, (int, float)):
                return float(price_value)
            if isinstance(price_value, str):
                # Parse price string (e.g., "£12.99", "$15.00", "12.99")
                try:
                    # Remove currency symbols and whitespace
                    cleaned = (
                        price_value.replace("£", "")
                        .replace("$", "")
                        .replace("€", "")
                        .strip()
                    )
                    return float(cleaned)
                except ValueError:
                    continue

    # Try nested price object
    if "priceInfo" in item and isinstance(item["priceInfo"], dict):
        price_info = item["priceInfo"]
        if "value" in price_info:
            try:
                return float(price_info["value"])
            except (ValueError, TypeError):
                pass

    return None


def _is_retryable_error(status_code: int) -> bool:
    """Check if an HTTP status code indicates a retryable error.

    Args:
        status_code: HTTP status code.

    Returns:
        True if the error is retryable, False otherwise.

    """
    # 429: Rate limit (retry after backoff)
    # 500, 502, 503, 504: Server errors (may be temporary)
    return status_code in (429, 500, 502, 503, 504)
