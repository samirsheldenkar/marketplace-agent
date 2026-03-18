"""Vinted scraper tool.

This module provides an async wrapper around the synchronous vinted-scraper library
for fetching marketplace listings and calculating price statistics.
"""

import asyncio
import statistics

import structlog

from src.config import get_settings
from src.exceptions import ScraperError
from src.models.state import PriceStats

logger = structlog.get_logger()

# Rate limiting: minimum seconds between requests
RATE_LIMIT_SECONDS = 1.0


def _extract_price(item: dict) -> float | None:
    """Extract price from a Vinted item dict.

    Args:
        item: Vinted item dictionary containing price information.

    Returns:
        Price as float, or None if extraction fails.

    """
    try:
        # Vinted items typically have a 'price' field with 'amount' or direct value
        price_data = item.get("price", {})
        if isinstance(price_data, dict):
            # Price might be in 'amount' or 'total_amount' field
            amount = price_data.get("amount") or price_data.get("total_amount")
            if amount is not None:
                return float(amount)
        elif isinstance(price_data, (int, float, str)):
            # Direct price value
            return float(price_data)

        # Fallback: try direct 'price' field as numeric
        price = item.get("price")
        if price is not None:
            if isinstance(price, dict):
                amount = price.get("amount") or price.get("total_amount")
                if amount is not None:
                    return float(amount)
            else:
                return float(price)

        # Another fallback: 'total_item_price' field
        total_price = item.get("total_item_price")
        if total_price is not None:
            if isinstance(total_price, dict):
                amount = total_price.get("amount") or total_price.get("total_amount")
                if amount is not None:
                    return float(amount)
            else:
                return float(total_price)

        return None
    except (TypeError, ValueError) as e:
        logger.warning(
            "Failed to extract price from item", error=str(e), item_id=item.get("id")
        )
        return None


def _sync_scrape(query: str, country: str, max_results: int) -> dict:
    """Synchronous scraping function to be run in a thread.

    Args:
        query: Search query string.
        country: Country code for Vinted marketplace (e.g., "GB", "FR").
        max_results: Maximum number of results to fetch.

    Returns:
        Raw search results from VintedScraper.

    Raises:
        ScraperError: If scraping fails.

    """
    from vinted_scraper import VintedScraper

    base_url = f"https://www.vinted.{country.lower()}"
    scraper = VintedScraper(base_url=base_url)

    try:
        result = scraper.search(params={"search_text": query, "per_page": max_results})
        return result
    except Exception as e:
        raise ScraperError(f"Vinted scraper failed for query '{query}': {e}") from e


async def scrape_vinted_listings(
    query: str,
    country: str = "GB",
    max_results: int = 50,
) -> PriceStats | None:
    """Scrape Vinted listings and calculate price statistics.

    This function wraps the synchronous vinted-scraper library with async
    compatibility, implementing timeout, retry logic, and rate limiting.

    Args:
        query: Search query string (e.g., "Nike Air Max 90").
        country: Country code for Vinted marketplace (default: "GB").
        max_results: Maximum number of results to fetch (default: 50).

    Returns:
        PriceStats dictionary with price statistics, or None on failure.

    Example:
        >>> stats = await scrape_vinted_listings("Nike Air Max 90")
        >>> if stats:
        ...     print(f"Average price: £{stats['avg_price']:.2f}")

    """
    settings = get_settings()
    timeout = settings.scraper_timeout_seconds
    max_retries = 2
    backoff_seconds = 2.0

    logger.info(
        "Starting Vinted scrape",
        query=query,
        country=country,
        max_results=max_results,
        timeout=timeout,
    )

    for attempt in range(max_retries + 1):
        try:
            # Run synchronous scraper in thread pool with timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(_sync_scrape, query, country, max_results),
                timeout=timeout,
            )

            # Extract items from result
            items = result.get("items", [])

            if not items:
                logger.warning("No items found in Vinted search", query=query)
                return None

            # Extract prices from items
            prices: list[float] = []
            valid_items: list[dict] = []

            for item in items:
                price = _extract_price(item)
                if price is not None and price > 0:
                    prices.append(price)
                    valid_items.append(item)

            if not prices:
                logger.warning(
                    "No valid prices extracted from Vinted items", query=query
                )
                return None

            # Calculate statistics
            num_listings = len(prices)
            avg_price = statistics.mean(prices)
            median_price = statistics.median(prices)
            min_price = min(prices)
            max_price = max(prices)

            price_stats: PriceStats = {
                "num_listings": num_listings,
                "avg_price": avg_price,
                "median_price": median_price,
                "min_price": min_price,
                "max_price": max_price,
                "items": valid_items,
            }

            logger.info(
                "Vinted scrape completed successfully",
                query=query,
                num_listings=num_listings,
                avg_price=avg_price,
                median_price=median_price,
            )

            return price_stats

        except TimeoutError:
            logger.warning(
                "Vinted scrape timeout",
                query=query,
                attempt=attempt + 1,
                max_retries=max_retries + 1,
            )
            if attempt < max_retries:
                # Linear backoff: 2s, 4s, etc.
                wait_time = backoff_seconds * (attempt + 1)
                logger.info("Retrying after timeout", wait_seconds=wait_time)
                await asyncio.sleep(wait_time)
                continue
            logger.error(
                "Vinted scrape failed after max retries",
                query=query,
                error="timeout",
            )
            return None

        except ScraperError as e:
            logger.warning(
                "Vinted scraper error",
                query=query,
                attempt=attempt + 1,
                max_retries=max_retries + 1,
                error=str(e),
            )
            if attempt < max_retries:
                # Linear backoff with rate limiting
                wait_time = backoff_seconds * (attempt + 1)
                # Ensure rate limiting between retries
                await asyncio.sleep(max(wait_time, RATE_LIMIT_SECONDS))
                continue
            logger.error(
                "Vinted scrape failed after max retries",
                query=query,
                error=str(e),
            )
            return None

        except Exception as e:
            logger.error(
                "Unexpected error during Vinted scrape",
                query=query,
                error=str(e),
                exc_info=True,
            )
            return None

    return None
