"""Agent decision node for pricing and platform recommendations.

This node analyzes price statistics from marketplace research and determines
the optimal listing price and preferred platform using LLM reasoning.
"""

import asyncio
from typing import Any

import structlog
from langchain_openai import ChatOpenAI

from src.agents.prompts.decision import (
    DECISION_SYSTEM,
    DECISION_USER,
    PricingDecision,
)
from src.config import get_settings
from src.exceptions import LLMError
from src.models.state import ListState, PriceStats
from src.services.pricing_service import PricingService

logger = structlog.get_logger()


# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds


def _format_price_stats(stats: PriceStats | None) -> str:
    """Format price statistics for LLM prompt.

    Args:
        stats: Price statistics from marketplace scraping, or None if unavailable.

    Returns:
        Formatted string describing the price statistics.

    """
    if stats is None:
        return "No data available"

    return f"""- Number of listings: {stats["num_listings"]}
- Average price: £{stats["avg_price"]:.2f}
- Median price: £{stats["median_price"]:.2f}
- Price range: £{stats["min_price"]:.2f} - £{stats["max_price"]:.2f}"""


async def agent_decision(state: ListState) -> dict[str, Any]:
    """Analyze price statistics and determine suggested price and preferred platform.

    This node uses PricingService for base calculations and LLM for refined
    decision-making with reasoning. If no price stats are available, it falls
    back to LLM-based estimation using item attributes.

    Args:
        state: Current LangGraph state containing price statistics from
            marketplace research and item identification data.

    Returns:
        Dictionary with updated state fields including:
            - suggested_price: Recommended listing price
            - preferred_platform: "ebay", "vinted", or "both"
            - platform_reasoning: Explanation of the decision

    Raises:
        LLMError: If LLM call fails after all retries.

    """
    settings = get_settings()

    # Initialize LLM client with structured output
    llm = ChatOpenAI(
        base_url=f"{settings.litellm_url}/v1",
        model=settings.reasoning_model,
        api_key=settings.litellm_api_key,
        temperature=0.1,
        max_tokens=2048,
    )
    structured_llm = llm.with_structured_output(PricingDecision)

    # Get price stats from state
    ebay_stats = state.get("ebay_price_stats")
    vinted_stats = state.get("vinted_price_stats")

    # Get item attributes for context
    item_type = state.get("item_type", "Unknown item")
    brand = state.get("brand") or "Unknown brand"
    condition = state.get("condition", "Good")
    condition_notes = state.get("condition_notes") or "None"
    fast_sale = state.get("fast_sale", True)

    # Calculate base price and platform using PricingService
    pricing_service = PricingService(settings)
    _calculated_price, _calculated_platform = pricing_service.calculate_suggested_price(
        ebay_stats, vinted_stats, fast_sale=fast_sale
    )

    # Format price stats for prompts
    ebay_stats_str = _format_price_stats(ebay_stats)
    vinted_stats_str = _format_price_stats(vinted_stats)

    # Build user prompt
    user_prompt = DECISION_USER.format(
        item_type=item_type,
        brand=brand,
        condition=condition,
        condition_notes=condition_notes,
        ebay_stats=ebay_stats_str,
        vinted_stats=vinted_stats_str,
    )

    # Call LLM with retry logic
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(
                "Calling decision LLM",
                attempt=attempt + 1,
                max_retries=MAX_RETRIES,
            )

            result: PricingDecision = await structured_llm.ainvoke(
                [
                    {"role": "system", "content": DECISION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ]
            )

            updates: dict[str, Any] = {
                "suggested_price": result.suggested_price,
                "preferred_platform": result.preferred_platform,
                "platform_reasoning": (
                    f"{result.platform_reasoning}\n\nPricing: {result.price_reasoning}"
                ),
            }

            logger.info(
                "Decision completed",
                suggested_price=result.suggested_price,
                preferred_platform=result.preferred_platform,
                has_ebay_stats=ebay_stats is not None,
                has_vinted_stats=vinted_stats is not None,
            )

            return updates

        except (LLMError, ValueError, TypeError) as e:
            last_error = e
            logger.warning(
                "LLM decision call failed",
                attempt=attempt + 1,
                error=str(e),
            )

        # Wait before retry (except on last attempt)
        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAYS[attempt]
            await asyncio.sleep(delay)

    # All retries exhausted
    error_msg = f"LLM decision failed after {MAX_RETRIES} attempts"
    logger.error(error_msg, last_error=str(last_error))
    raise LLMError(error_msg)
