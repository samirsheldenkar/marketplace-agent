"""Agent reasoning node for analysis and planning.

This node merges image analysis results with user-provided metadata
and builds optimized search queries for marketplace price research.
"""

import asyncio
import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI

from src.agents.prompts.reasoning import (
    REASONING_SYSTEM,
    REASONING_USER,
    ReasoningResult,
)
from src.config import get_settings
from src.exceptions import LLMError
from src.models.state import ListState

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds


async def agent_reasoning(state: ListState) -> dict[str, Any]:
    """Analyze item information and build optimized search queries.

    This node merges image analysis results with user-provided metadata,
    calls the LLM to refine item attributes, and constructs optimized
    search queries for eBay and Vinted platforms.

    Args:
        state: Current LangGraph state containing image analysis results
            and optional user metadata.

    Returns:
        Dictionary with updated state fields including:
            - item_type: Normalized item type
            - brand: Item brand if identified
            - model_name: Model name/number if applicable
            - size: Size specification
            - color: Primary color
            - condition: Item condition
            - condition_notes: Additional condition details
            - accessories_included: List of included accessories
            - confidence: Confidence score (0.0-1.0)
            - ebay_query_used: Optimized eBay search query
            - vinted_query_used: Optimized Vinted search query
            - needs_clarification: Whether clarification is needed

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
        max_tokens=4096,
    )

    # Extract image analysis data from state
    image_analysis = state.get("image_analysis_raw") or {}

    # Build user metadata from state fields
    user_metadata: dict[str, Any] = {}
    if brand := state.get("brand"):
        user_metadata["brand"] = brand
    if model_name := state.get("model_name"):
        user_metadata["model_name"] = model_name
    if size := state.get("size"):
        user_metadata["size"] = size
    if color := state.get("color"):
        user_metadata["color"] = color
    if condition := state.get("condition"):
        user_metadata["condition"] = condition
    if condition_notes := state.get("condition_notes"):
        user_metadata["condition_notes"] = condition_notes
    if accessories := state.get("accessories_included"):
        user_metadata["accessories_included"] = accessories
    if item_description := state.get("item_description"):
        user_metadata["notes"] = item_description

    # Format prompts
    system_prompt = REASONING_SYSTEM
    user_prompt = REASONING_USER.format(
        image_analysis=json.dumps(image_analysis, indent=2),
        user_metadata=json.dumps(user_metadata, indent=2)
        if user_metadata
        else "None provided",
    )

    # Call LLM with retry logic
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(
                "Calling reasoning LLM",
                extra={"attempt": attempt + 1, "max_retries": MAX_RETRIES},
            )

            response = await llm.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
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
                result = ReasoningResult(**result_dict)
            else:
                raise LLMError("Unexpected response type from LLM")

            # Build response state updates
            updates: dict[str, Any] = {
                "item_type": result.item_type,
                "brand": result.brand,
                "model_name": result.model_name,
                "size": result.size,
                "color": result.color,
                "condition": result.condition,
                "condition_notes": result.condition_notes,
                "accessories_included": result.accessories_included,
                "confidence": result.confidence,
                "ebay_query_used": result.ebay_query_used,
                "vinted_query_used": result.vinted_query_used,
                "needs_clarification": result.confidence
                < settings.confidence_threshold,
            }

            logger.info(
                "Reasoning completed",
                extra={
                    "item_type": result.item_type,
                    "confidence": result.confidence,
                    "needs_clarification": updates["needs_clarification"],
                },
            )

            return updates

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(
                "Failed to parse LLM response as JSON",
                extra={"attempt": attempt + 1, "error": str(e)},
            )
        except Exception as e:
            last_error = e
            logger.warning(
                "LLM call failed",
                extra={"attempt": attempt + 1, "error": str(e)},
            )

        # Wait before retry (except on last attempt)
        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAYS[attempt]
            logger.debug(f"Retrying in {delay}s...")
            await asyncio.sleep(delay)

    # All retries exhausted
    error_msg = f"LLM reasoning failed after {MAX_RETRIES} attempts"
    logger.error(error_msg, extra={"last_error": str(last_error)})
    raise LLMError(error_msg)
