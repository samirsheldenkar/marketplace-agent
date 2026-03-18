"""LangGraph state definitions."""

import operator
from typing import Annotated, Any, TypedDict


class PriceStats(TypedDict):
    """Price statistics from marketplace scraping."""

    num_listings: int
    avg_price: float
    median_price: float
    min_price: float
    max_price: float
    items: list[dict]


class ListingDraft(TypedDict):
    """Generated listing content."""

    title: str
    description: str
    category_suggestions: list[str]
    shipping_suggestion: str
    returns_policy: str
    platform_variants: dict[str, dict]


class ListState(TypedDict, total=False):
    """Complete agent state for LangGraph.

    Tracks the progress of a listing through the agent pipeline.
    """

    # Control
    run_id: str
    messages: list[Any]

    # Item identification
    item_description: str
    item_type: str
    brand: str | None
    model_name: str | None
    size: str | None
    color: str | None
    condition: str  # "New" | "Excellent" | "Good" | "Fair" | "Poor"
    condition_notes: str | None
    confidence: float
    accessories_included: list[str]

    # Images
    photos: list[str]
    image_analysis_raw: dict | None

    # Price research
    ebay_price_stats: PriceStats | None
    vinted_price_stats: PriceStats | None
    ebay_query_used: str | None
    vinted_query_used: str | None

    # Decision
    suggested_price: float | None
    preferred_platform: str | None  # "ebay" | "vinted" | "both"
    platform_reasoning: str | None
    fast_sale: bool  # User preference for discount pricing

    # Output
    listing_draft: ListingDraft | None

    # Control flow
    needs_clarification: bool
    clarification_question: str | None
    error_state: str | None
    retry_count: Annotated[int, operator.add]
