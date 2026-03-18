"""Quality check node for listing validation.

This module provides deterministic validation of generated listing content
against quality constraints. It checks title length, description word count,
required fields, price reasonableness, and placeholder text detection.
"""

import logging
import re

from src.models.state import ListState

logger = logging.getLogger(__name__)

# Constants for validation
MAX_TITLE_LENGTH = 80
MIN_DESCRIPTION_WORDS = 200
MAX_DESCRIPTION_WORDS = 400
MAX_RETRY_COUNT = 1

# Placeholder patterns to detect
PLACEHOLDER_PATTERNS = [
    r"\[insert[^\]]*\]",  # [insert...], [insert price], etc.
    r"\[TODO[^\]]*\]",  # [TODO], [TODO: add details], etc.
    r"\[placeholder[^\]]*\]",  # [placeholder], [placeholder text], etc.
    r"\bTODO\b",  # Standalone TODO
    r"\bPLACEHOLDER\b",  # Standalone PLACEHOLDER
    r"\bTBD\b",  # To be determined
    r"\bFIXME\b",  # Fix marker pattern
]


def _count_words(text: str) -> int:
    """Count words in a text string.

    Args:
        text: The text to count words in.

    Returns:
        Number of words in the text.

    """
    if not text:
        return 0
    # Split on whitespace and filter empty strings
    words = text.split()
    return len(words)


def _contains_placeholder(text: str) -> bool:
    """Check if text contains placeholder patterns.

    Args:
        text: The text to check for placeholders.

    Returns:
        True if placeholder patterns are found, False otherwise.

    """
    if not text:
        return False

    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _get_median_price(state: ListState) -> float | None:
    """Get the median price from available price statistics.

    Prioritizes eBay median if available, falls back to Vinted median.

    Args:
        state: Current agent state.

    Returns:
        Median price if available, None otherwise.

    """
    # Check eBay price stats first
    ebay_stats = state.get("ebay_price_stats")
    if ebay_stats and ebay_stats.get("median_price"):
        return ebay_stats["median_price"]

    # Fall back to Vinted price stats
    vinted_stats = state.get("vinted_price_stats")
    if vinted_stats and vinted_stats.get("median_price"):
        return vinted_stats["median_price"]

    return None


def _validate_title(title: str | None) -> list[str]:
    """Validate the listing title.

    Args:
        title: The listing title to validate.

    Returns:
        List of validation issues found.

    """
    issues: list[str] = []

    if not title:
        issues.append("Title is missing or empty")
        return issues

    if not title.strip():
        issues.append("Title is empty or contains only whitespace")
        return issues

    if len(title) > MAX_TITLE_LENGTH:
        issues.append(
            f"Title exceeds maximum length of {MAX_TITLE_LENGTH} characters "
            f"(current: {len(title)} characters)"
        )

    if _contains_placeholder(title):
        issues.append("Title contains placeholder text")

    return issues


def _validate_description(description: str | None) -> list[str]:
    """Validate the listing description.

    Args:
        description: The listing description to validate.

    Returns:
        List of validation issues found.

    """
    issues: list[str] = []

    if not description:
        issues.append("Description is missing or empty")
        return issues

    if not description.strip():
        issues.append("Description is empty or contains only whitespace")
        return issues

    word_count = _count_words(description)

    if word_count < MIN_DESCRIPTION_WORDS:
        issues.append(
            f"Description has too few words: {word_count} "
            f"(minimum: {MIN_DESCRIPTION_WORDS} words)"
        )
    elif word_count > MAX_DESCRIPTION_WORDS:
        issues.append(
            f"Description exceeds maximum word count: {word_count} "
            f"(maximum: {MAX_DESCRIPTION_WORDS} words)"
        )

    if _contains_placeholder(description):
        issues.append("Description contains placeholder text")

    return issues


def _validate_price(state: ListState) -> list[str]:
    """Validate the suggested price.

    Args:
        state: Current agent state containing suggested_price and price stats.

    Returns:
        List of validation issues found.

    """
    issues: list[str] = []

    suggested_price = state.get("suggested_price")

    if suggested_price is None:
        # Price is optional at this stage - may be set later
        return issues

    if suggested_price <= 0:
        issues.append(f"Price must be positive (current: {suggested_price})")
        return issues

    # Check if price is reasonable compared to median
    median_price = _get_median_price(state)
    if median_price is not None:
        # Price should be within 2x of median (reasonable range)
        max_reasonable_price = median_price * 2
        min_reasonable_price = median_price * 0.5  # Also check if too low

        if suggested_price > max_reasonable_price:
            issues.append(
                f"Price ${suggested_price:.2f} seems too high compared to "
                f"market median ${median_price:.2f} (should be within 2x)"
            )
        elif suggested_price < min_reasonable_price:
            issues.append(
                f"Price ${suggested_price:.2f} seems too low compared to "
                f"market median ${median_price:.2f} (should be at least 50% of median)"
            )

    return issues


def quality_check(state: ListState) -> dict:
    """Perform deterministic validation of listing content.

    This node validates the generated listing content against quality constraints
    without using any LLM calls. It checks:
    - Title length (≤ 80 characters)
    - Description word count (200-400 words)
    - Required fields populated (title, description not empty)
    - Price is positive and reasonable (within 2x of median if available)
    - No placeholder text patterns

    Args:
        state: Current agent state containing listing_draft and price info.

    Returns:
        Dictionary with state updates:
            - quality_passed: True if all checks pass, False otherwise
            - quality_issues: List of descriptions for any issues found

    """
    logger.info(
        "Starting quality check",
        extra={
            "has_listing_draft": state.get("listing_draft") is not None,
            "has_suggested_price": state.get("suggested_price") is not None,
        },
    )

    issues: list[str] = []

    # Get listing draft
    listing_draft = state.get("listing_draft")

    if listing_draft is None:
        issues.append("No listing draft generated")
        logger.warning("Quality check failed: no listing draft")
        return {
            "quality_passed": False,
            "quality_issues": issues,
        }

    # Validate title
    title = listing_draft.get("title")
    title_issues = _validate_title(title)
    issues.extend(title_issues)

    # Validate description
    description = listing_draft.get("description")
    description_issues = _validate_description(description)
    issues.extend(description_issues)

    # Validate price
    price_issues = _validate_price(state)
    issues.extend(price_issues)

    # Determine if quality check passed
    quality_passed = len(issues) == 0

    if quality_passed:
        logger.info("Quality check passed")
    else:
        logger.warning(
            "Quality check failed",
            extra={"issue_count": len(issues), "issues": issues},
        )

    result = {
        "quality_passed": quality_passed,
        "quality_issues": issues,
    }

    if not quality_passed:
        result["retry_count"] = 1

    return result


def should_retry(state: ListState) -> bool:
    """Determine if the listing generation should be retried.

    Returns True if quality check failed and we haven't exceeded the maximum
    retry count. This is used as a conditional edge in the LangGraph workflow.

    Args:
        state: Current agent state containing quality_passed and retry_count.

    Returns:
        True if we should retry listing generation, False otherwise.

    """
    quality_passed = state.get("quality_passed", False)
    retry_count = state.get("retry_count", 0)

    # Retry if quality failed and we haven't hit the max retry count
    should_retry_result = not quality_passed and retry_count < MAX_RETRY_COUNT

    logger.debug(
        "Checking retry condition",
        extra={
            "quality_passed": quality_passed,
            "retry_count": retry_count,
            "should_retry": should_retry_result,
        },
    )

    return should_retry_result
