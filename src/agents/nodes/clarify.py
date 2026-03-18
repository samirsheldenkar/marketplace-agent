"""Clarification node for generating targeted questions when confidence is low.

This module provides nodes for requesting user clarification when the agent
needs additional information to create a high-quality listing.
"""

from typing import Any

import structlog
from langchain_openai import ChatOpenAI

from src.agents.prompts.clarification import (
    CLARIFICATION_SYSTEM,
    CLARIFICATION_USER,
    ClarificationResult,
)
from src.config import get_settings
from src.exceptions import LLMError
from src.models.state import ListState

logger = structlog.get_logger()


def _build_context(state: ListState) -> dict[str, Any]:
    """Build context dictionary from current state for prompt formatting.

    Args:
        state: Current agent state.

    Returns:
        Dictionary with item attributes for prompt formatting.

    """
    return {
        "item_description": state.get("item_description", "Unknown"),
        "item_type": state.get("item_type", "Unknown"),
        "brand": state.get("brand") or "Not specified",
        "model_name": state.get("model_name") or "Not specified",
        "size": state.get("size") or "Not specified",
        "color": state.get("color") or "Not specified",
        "condition": state.get("condition", "Unknown"),
        "condition_notes": state.get("condition_notes") or "Not specified",
        "accessories_included": state.get("accessories_included", []),
        "confidence": state.get("confidence", 0.0),
    }


def _get_llm() -> ChatOpenAI:
    """Create configured LLM instance for clarification.

    Returns:
        Configured ChatOpenAI instance.

    """
    settings = get_settings()
    return ChatOpenAI(
        model=settings.reasoning_model,
        base_url=f"{settings.litellm_url}/v1",
        api_key=settings.litellm_api_key,
        temperature=0.3,
    )


async def clarify(state: ListState) -> dict:
    """Generate targeted clarification question when confidence is low.

    This node analyzes the current state and generates a friendly question
    to gather missing information from the user. The graph will halt when
    needs_clarification=True, waiting for user response.

    Args:
        state: Current agent state containing item information.

    Returns:
        Dictionary with state updates:
            - needs_clarification: True (signals graph to halt)
            - clarification_question: The generated question
            - error_state: None (clears any previous errors)
            - clarification_count: Incremented clarification round counter

    Raises:
        LLMError: If the LLM call fails.

    """
    logger.info(
        "Generating clarification question",
        item_type=state.get("item_type"),
        confidence=state.get("confidence"),
        clarification_count=state.get("clarification_count", 0),
    )

    # Track clarification rounds
    current_count = state.get("clarification_count", 0)

    try:
        llm = _get_llm()
        context = _build_context(state)

        # Format the user prompt with current state
        user_prompt = CLARIFICATION_USER.format(**context)

        # Call LLM with structured output
        structured_llm = llm.with_structured_output(ClarificationResult)
        result: ClarificationResult = await structured_llm.ainvoke(
            [
                {"role": "system", "content": CLARIFICATION_SYSTEM},
                {"role": "user", "content": user_prompt},
            ]
        )

        # Check if clarification is actually needed
        if result.confidence_threshold_met and not result.missing_fields:
            logger.info(
                "No clarification needed, confidence threshold met",
                confidence_threshold_met=result.confidence_threshold_met,
            )
            return {
                "needs_clarification": False,
                "clarification_question": None,
                "error_state": None,
            }

        # Generate the clarification question
        question = result.clarification_question
        if not question:
            # Fallback question if LLM didn't provide one
            missing = result.missing_fields or ["additional details"]
            question = (
                f"Could you provide more information about the {' and '.join(missing)}?"
            )

        logger.info(
            "Clarification question generated",
            question=question,
            missing_fields=result.missing_fields,
            reasoning=result.reasoning,
        )

        return {
            "needs_clarification": True,
            "clarification_question": question,
            "error_state": None,
            "clarification_count": current_count + 1,
        }

    except Exception as e:
        logger.exception("Failed to generate clarification question")
        raise LLMError(f"Failed to generate clarification question: {e}") from e


def _extract_field_updates(user_answer: str) -> dict[str, Any]:  # noqa: C901
    """Extract structured field updates from user's free-form answer.

    This is a simple extraction that looks for common patterns in user answers.
    For more complex extraction, the LLM could be used.

    Args:
        user_answer: The user's response to the clarification question.

    Returns:
        Dictionary of extracted field updates.

    """
    updates: dict[str, Any] = {}
    answer_lower = user_answer.lower()

    # Simple pattern matching for common fields
    # These patterns are intentionally simple; complex extraction should use LLM

    # Brand detection (look for "brand is X" or "it's a X")
    if "brand is" in answer_lower:
        parts = user_answer.lower().split("brand is")
        if len(parts) > 1:
            brand = parts[1].strip().split()[0].strip(".,!?")
            updates["brand"] = brand.capitalize()

    # Size detection (look for size patterns)
    size_patterns = [
        "size is",
        "it's a size",
        "the size is",
    ]
    for pattern in size_patterns:
        if pattern in answer_lower:
            parts = user_answer.lower().split(pattern)
            if len(parts) > 1:
                size = parts[1].strip().split()[0].strip(".,!?")
                updates["size"] = size.upper() if size.isalpha() else size
                break

    # Model detection
    if "model is" in answer_lower:
        parts = user_answer.lower().split("model is")
        if len(parts) > 1:
            model = parts[1].strip().split(".")[0].strip()
            updates["model_name"] = model

    # Color detection
    if "color is" in answer_lower:
        parts = user_answer.lower().split("color is")
        if len(parts) > 1:
            color = parts[1].strip().split()[0].strip(".,!?")
            updates["color"] = color.capitalize()

    # Condition detection
    condition_keywords = {
        "new": "New",
        "excellent": "Excellent",
        "good": "Good",
        "fair": "Fair",
        "poor": "Poor",
    }
    for keyword, condition in condition_keywords.items():
        if (
            f"condition is {keyword}" in answer_lower
            or f"it's in {keyword}" in answer_lower
        ):
            updates["condition"] = condition
            break

    return updates


async def resume_after_clarification(state: ListState, user_answer: str) -> dict:
    """Process user's answer to clarification question and update state.

    This function is called when the user responds to a clarification question.
    It parses the answer, extracts relevant information, and merges it into
    the state.

    Args:
        state: Current agent state (before user answer).
        user_answer: The user's response to the clarification question.

    Returns:
        Dictionary with state updates:
            - Updated fields extracted from the answer
            - needs_clarification: False (resume normal flow)
            - clarification_question: None (clear the question)
            - error_state: None

    """
    logger.info(
        "Processing user clarification response",
        extra={
            "user_answer_length": len(user_answer),
            "current_item_type": state.get("item_type"),
        },
    )

    # Extract field updates from the answer
    extracted_updates = _extract_field_updates(user_answer)

    # If we couldn't extract structured data, store the answer as condition notes
    # or append to existing description
    if not extracted_updates:
        # Store as additional context
        existing_notes = state.get("condition_notes") or ""
        if existing_notes:
            new_notes = f"{existing_notes}. User clarification: {user_answer}"
        else:
            new_notes = f"User clarification: {user_answer}"
        extracted_updates["condition_notes"] = new_notes

    # Merge extracted info into state
    logger.info(
        "Extracted updates from clarification",
        extra={"extracted_fields": list(extracted_updates.keys())},
    )

    return {
        **extracted_updates,
        "needs_clarification": False,
        "clarification_question": None,
        "error_state": None,
    }
