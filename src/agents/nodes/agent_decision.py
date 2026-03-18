"""Agent decision node for pricing and platform recommendations.

This node analyzes price statistics from marketplace research and determines
the optimal listing price and preferred platform using LLM reasoning.
"""

import asyncio
import json
import logging
from typing import Any

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

logger = logging.getLogger(__name__)

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


def _raise_unexpected_type() -> None:
    """Raise LLMError for unexpected response type.

    This helper function abstracts the raise statement to satisfy TRY301.

    Raises:
        LLMError: Always raised with unexpected response type message.

    """
    raise LLMError("Unexpected response type from LLM")


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

    # Initialize LLM client
    llm = ChatOpenAI(
        base_url=f"{settings.litellm_url}/v1",
        model=settings.reasoning_model,
        api_key=settings.litellm_api_key,
        temperature=0.1,
        max_tokens=2048,
    )

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
                extra={"attempt": attempt + 1, "max_retries": MAX_RETRIES},
            )

            response = await llm.ainvoke(
                [
                    {"role": "system", "content": DECISION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ]
            )

            # Parse the response content
            content = response.content
            if isinstance(content, str):
                # Try to extract JSON from the response
                content_text = content.strip()
                # Handle potential markdown code blocks
                if content_text.startswith("```"):
                    lines = content_text.split("\n")
                    # Remove first and last line if they're code block markers
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    content_text = "\n".join(lines)

                # Parse JSON response
                result_dict = json.loads(content_text)
                result = PricingDecision(**result_dict)
            else:
                raise _raise_unexpected_type()

            # Build response state updates
            updates: dict[str, Any] = {
                "suggested_price": result.suggested_price,
                "preferred_platform": result.preferred_platform,
                "platform_reasoning": (
                    f"{result.platform_reasoning}\n\nPricing: {result.price_reasoning}"
                ),
            }

            logger.info(
                "Decision completed",
                extra={
                    "suggested_price": result.suggested_price,
                    "preferred_platform": result.preferred_platform,
                    "has_ebay_stats": ebay_stats is not None,
                    "has_vinted_stats": vinted_stats is not None,
                },
            )

            return updates

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(
                "Failed to parse LLM response as JSON",
                extra={"attempt": attempt + 1, "error": str(e)},
            )
        except (LLMError, ValueError, TypeError) as e:
            last_error = e
            logger.warning(
                "LLM call failed",
                extra={"attempt": attempt + 1, "error": str(e)},
            )

        # Wait before retry (except on last attempt)
        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAYS[attempt]
            logger.debug("Retrying in %ss...", delay)
            await asyncio.sleep(delay)

    # All retries exhausted
    error_msg = f"LLM decision failed after {MAX_RETRIES} attempts"
    logger.error(error_msg, extra={"last_error": str(last_error)})
    raise LLMError(error_msg)
