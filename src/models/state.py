"""LangGraph state definitions."""

from typing import Any, List, Optional, TypedDict


class PriceStats(TypedDict):
    """Price statistics from marketplace scraping."""

    num_listings: int
    avg_price: float
    median_price: float
    min_price: float
    max_price: float
    items: List[dict]


class ListingDraft(TypedDict):
    """Generated listing content."""

    title: str
    description: str
    category_suggestions: List[str]
    shipping_suggestion: str
    returns_policy: str
    platform_variants: dict[str, dict]


class ListState(TypedDict, total=False):
    """Complete agent state for LangGraph.

    Tracks the progress of a listing through the agent pipeline.
    """

    # Control
    run_id: str
    messages: List[Any]

    # Item identification
    item_description: str
    item_type: str
    brand: Optional[str]
    model_name: Optional[str]
    size: Optional[str]
    color: Optional[str]
    condition: str  # "New" | "Excellent" | "Good" | "Fair" | "Poor"
    condition_notes: Optional[str]
    confidence: float
    accessories_included: List[str]

    # Images
    photos: List[str]
    image_analysis_raw: Optional[dict]

    # Price research
    ebay_price_stats: Optional[PriceStats]
    vinted_price_stats: Optional[PriceStats]
    ebay_query_used: Optional[str]
    vinted_query_used: Optional[str]

    # Decision
    suggested_price: Optional[float]
    preferred_platform: Optional[str]  # "ebay" | "vinted" | "both"
    platform_reasoning: Optional[str]

    # Output
    listing_draft: Optional[ListingDraft]

    # Control flow
    needs_clarification: bool
    clarification_question: Optional[str]
    error_state: Optional[str]
    retry_count: int
