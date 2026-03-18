"""Vinted scraper node.

This LangGraph node calls the Vinted scraper tool and stores results in state.
"""

import structlog

from src.config import get_settings
from src.models.state import ListState, PriceStats
from src.tools.vinted_scraper import scrape_vinted_listings

logger = structlog.get_logger()


async def scrape_vinted(state: ListState) -> dict:
    """Scrape Vinted listings and update state with price statistics.

    This node retrieves the search query from state (set by agent_reasoning),
    calls the Vinted scraper tool, and returns price statistics.

    On failure, the node continues gracefully without raising exceptions,
    allowing the agent to proceed with eBay data only.

    Args:
        state: Current LangGraph state containing vinted_query_used.

    Returns:
        Dictionary with state updates:
            - vinted_price_stats: PriceStats dict or None if failed
            - error_state: Error message if failed, else None

    """
    settings = get_settings()
    query: str | None = state.get("vinted_query_used")

    if not query:
        logger.warning("No Vinted query provided in state")
        return {
            "vinted_price_stats": None,
            "vinted_error": "No Vinted search query available",
        }

    logger.info(
        "Starting Vinted scraper node",
        query=query,
        country=settings.vinted_country,
        max_results=settings.max_scraper_results,
    )

    try:
        price_stats: PriceStats | None = await scrape_vinted_listings(
            query=query,
            country=settings.vinted_country,
            max_results=settings.max_scraper_results,
        )

        if price_stats is None:
            logger.warning(
                "Vinted scraper returned no results",
                query=query,
            )
            return {
                "vinted_price_stats": None,
                "vinted_error": f"Vinted scraper returned no results for query: {query}",
            }

        logger.info(
            "Vinted scraper completed successfully",
            query=query,
            num_listings=price_stats["num_listings"],
            avg_price=price_stats["avg_price"],
            median_price=price_stats["median_price"],
        )

        return {
            "vinted_price_stats": price_stats,
            "vinted_error": None,
        }

    except Exception as e:
        logger.exception(
            "Vinted scraper node failed unexpectedly",
            query=query,
            error=str(e),
        )
        return {
            "vinted_price_stats": None,
            "vinted_error": f"Vinted scraper failed: {e!s}",
        }
