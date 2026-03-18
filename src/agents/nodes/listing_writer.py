"""Listing writer node for generating marketplace listings.

This node generates listing title, description, and other content
using the drafting model (Ollama/Llama 3) with graceful fallback
to the reasoning model if needed.
"""

import asyncio
from typing import Any

import structlog
from langchain_openai import ChatOpenAI

from src.agents.prompts.listing_writer import (
    WRITER_SYSTEM,
    WRITER_USER,
    ListingDraftResult,
)
from src.config import get_settings
from src.exceptions import LLMError
from src.models.state import ListState

logger = structlog.get_logger()

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds


def _build_price_research_summary(state: ListState) -> str:
    """Build a human-readable summary of price research data.

    Args:
        state: Current LangGraph state containing price research data.

    Returns:
        Formatted string summarizing price research from both platforms.

    """
    lines = []

    # eBay price research
    ebay_stats = state.get("ebay_price_stats")
    if ebay_stats:
        lines.append("eBay Market Data:")
        lines.append(
            f"  - {ebay_stats.get('num_listings', 0)} comparable listings found"
        )
        lines.append(f"  - Average price: £{ebay_stats.get('avg_price', 0):.2f}")
        lines.append(f"  - Median price: £{ebay_stats.get('median_price', 0):.2f}")
        min_price = ebay_stats.get("min_price", 0)
        max_price = ebay_stats.get("max_price", 0)
        lines.append(f"  - Price range: £{min_price:.2f} - £{max_price:.2f}")

    # Vinted price research
    vinted_stats = state.get("vinted_price_stats")
    if vinted_stats:
        lines.append("Vinted Market Data:")
        lines.append(
            f"  - {vinted_stats.get('num_listings', 0)} comparable listings found"
        )
        lines.append(f"  - Average price: £{vinted_stats.get('avg_price', 0):.2f}")
        lines.append(f"  - Median price: £{vinted_stats.get('median_price', 0):.2f}")
        min_price = vinted_stats.get("min_price", 0)
        max_price = vinted_stats.get("max_price", 0)
        lines.append(f"  - Price range: £{min_price:.2f} - £{max_price:.2f}")

    if not lines:
        return "No price research data available."

    return "\n".join(lines)


def _format_optional(value: Any, default: str = "Not specified") -> str:
    """Format an optional value for display.

    Args:
        value: The value to format (may be None).
        default: Default string to use if value is None or empty.

    Returns:
        Formatted string representation.

    """
    if value is None:
        return default
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else default
    return str(value) if str(value).strip() else default


async def _call_llm_with_retry(
    llm: ChatOpenAI,
    system_prompt: str,
    user_prompt: str,
    model_name: str,
) -> ListingDraftResult:
    """Call LLM with structured output and retry logic.

    Args:
        llm: The ChatOpenAI instance to use.
        system_prompt: System prompt for the LLM.
        user_prompt: User prompt for the LLM.
        model_name: Name of the model being used (for logging).

    Returns:
        Parsed ListingDraftResult from the LLM response.

    Raises:
        LLMError: If all retries fail.

    """
    structured_llm = llm.with_structured_output(ListingDraftResult)
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(
                "Calling drafting LLM",
                attempt=attempt + 1,
                max_retries=MAX_RETRIES,
                model=model_name,
            )

            result: ListingDraftResult = await structured_llm.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )

            logger.info(
                "Listing draft generated successfully",
                model=model_name,
                title_length=len(result.title),
                description_length=len(result.description),
            )

            return result

        except (LLMError, ValueError, TypeError) as e:
            last_error = e
            logger.warning(
                "LLM drafting call failed",
                attempt=attempt + 1,
                error=str(e),
                model=model_name,
            )

        # Wait before retry (except on last attempt)
        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAYS[attempt]
            await asyncio.sleep(delay)

    # All retries exhausted
    error_msg = f"LLM listing generation failed after {MAX_RETRIES} attempts"
    logger.error(error_msg, last_error=str(last_error))
    raise LLMError(error_msg)


async def listing_writer(state: ListState) -> dict[str, Any]:
    """Generate listing content using the drafting model.

    This node takes item attributes, pricing information, and platform decision
    from the state and generates a complete listing draft including title,
    description, categories, shipping, and platform-specific variants.

    If the drafting model fails, it gracefully falls back to the reasoning model.

    Args:
        state: Current LangGraph state containing item attributes,
            pricing data, and platform decision.

    Returns:
        Dictionary with updated state fields including:
            - listing_draft: Generated listing content with title,
              description, categories, shipping, and platform variants.

    Raises:
        LLMError: If both drafting and reasoning models fail.

    """
    settings = get_settings()

    # Build context from state
    item_type = _format_optional(state.get("item_type"))
    brand = _format_optional(state.get("brand"))
    model_name = _format_optional(state.get("model_name"))
    size = _format_optional(state.get("size"))
    color = _format_optional(state.get("color"))
    condition = _format_optional(state.get("condition"))
    condition_notes = _format_optional(state.get("condition_notes"))
    accessories_included = _format_optional(state.get("accessories_included"))
    item_description = _format_optional(state.get("item_description"))
    suggested_price = state.get("suggested_price", 0.0) or 0.0
    preferred_platform = _format_optional(state.get("preferred_platform"), "ebay")

    # Build price research summary
    price_research_summary = _build_price_research_summary(state)

    # Format user prompt
    user_prompt = WRITER_USER.format(
        item_type=item_type,
        brand=brand,
        model_name=model_name,
        size=size,
        color=color,
        condition=condition,
        condition_notes=condition_notes,
        accessories_included=accessories_included,
        item_description=item_description,
        suggested_price=f"{suggested_price:.2f}",
        preferred_platform=preferred_platform,
        price_research_summary=price_research_summary,
    )

    # Try drafting model first
    drafting_llm = ChatOpenAI(
        base_url=f"{settings.litellm_url}/v1",
        model=settings.drafting_model,
        api_key=settings.litellm_api_key,
        temperature=0.7,
        max_tokens=4096,
    )

    try:
        result = await _call_llm_with_retry(
            drafting_llm,
            WRITER_SYSTEM,
            user_prompt,
            settings.drafting_model,
        )

        return {
            "listing_draft": {
                "title": result.title,
                "description": result.description,
                "category_suggestions": result.category_suggestions,
                "shipping_suggestion": result.shipping_suggestion,
                "returns_policy": result.returns_policy,
                "platform_variants": result.platform_variants,
            }
        }

    except LLMError:
        # Graceful degradation: fall back to reasoning model
        logger.warning(
            "Drafting model failed, falling back to reasoning model",
            drafting_model=settings.drafting_model,
            reasoning_model=settings.reasoning_model,
        )

        reasoning_llm = ChatOpenAI(
            base_url=f"{settings.litellm_url}/v1",
            model=settings.reasoning_model,
            api_key=settings.litellm_api_key,
            temperature=0.7,
            max_tokens=4096,
        )

        result = await _call_llm_with_retry(
            reasoning_llm,
            WRITER_SYSTEM,
            user_prompt,
            settings.reasoning_model,
        )

        return {
            "listing_draft": {
                "title": result.title,
                "description": result.description,
                "category_suggestions": result.category_suggestions,
                "shipping_suggestion": result.shipping_suggestion,
                "returns_policy": result.returns_policy,
                "platform_variants": result.platform_variants,
            }
        }
