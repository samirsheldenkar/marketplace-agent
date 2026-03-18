"""eBay scraper node for LangGraph workflow.

This node calls the eBay scraper tool and stores results in state.
It handles failures gracefully, allowing the agent to continue with
Vinted data if eBay scraping fails.
"""

import structlog

from src.config import get_settings
from src.models.state import ListState
from src.tools.ebay_scraper import scrape_ebay_sold_listings

logger = structlog.get_logger()


async def scrape_ebay(state: ListState) -> dict:
    """Scrape eBay sold listings and update state with price statistics.

    This is a LangGraph node that fetches sold listing data from eBay
    to help determine market pricing. It handles failures gracefully,
    returning an error state rather than raising exceptions.

    Args:
        state: Current agent state containing ebay_query_used from
            the agent_reasoning node.

    Returns:
        Dictionary with state updates:
            - ebay_price_stats: PriceStats dict or None if failed
            - error_state: Error message if failed, else None

    """
    settings = get_settings()
    query = state.get("ebay_query_used")

    # Check if query was provided by agent_reasoning
    if not query:
        logger.warning(
            "No eBay query provided in state",
            run_id=state.get("run_id"),
        )
        return {
            "ebay_price_stats": None,
            "ebay_error": "No eBay search query provided",
        }

    logger.info(
        "Starting eBay scrape",
        query=query,
        country=settings.ebay_country,
        max_results=settings.max_scraper_results,
        run_id=state.get("run_id"),
    )

    try:
        price_stats = await scrape_ebay_sold_listings(
            query=query,
            country=settings.ebay_country,
            max_results=settings.max_scraper_results,
        )

        if price_stats is None:
            logger.warning(
                "eBay scraper returned no results",
                query=query,
                run_id=state.get("run_id"),
            )
            return {
                "ebay_price_stats": None,
                "ebay_error": f"eBay scraper failed for query: {query}",
            }

        logger.info(
            "eBay scrape completed successfully",
            query=query,
            num_listings=price_stats["num_listings"],
            avg_price=price_stats["avg_price"],
            run_id=state.get("run_id"),
        )

        return {
            "ebay_price_stats": price_stats,
            "ebay_error": None,
        }

    except Exception as e:
        # Log error but continue gracefully - agent can use Vinted only
        logger.exception(
            "eBay scraper encountered an error",
            query=query,
            run_id=state.get("run_id"),
        )
        return {
            "ebay_price_stats": None,
            "ebay_error": f"eBay scraper error: {e!s}",
        }
