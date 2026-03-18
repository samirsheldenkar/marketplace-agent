"""LangGraph state definitions."""

from typing import Any, NotRequired, TypedDict


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


class ListState(TypedDict):
    """Complete agent state for LangGraph.

    Tracks the progress of a listing through the agent pipeline.
    Required fields must be present in the initial state dict passed to the graph.
    NotRequired fields are populated by agent nodes during execution.
    """

    # Control (required at graph start)
    run_id: str
    messages: list[Any]
    photos: list[str]
    needs_clarification: bool
    fast_sale: bool
    confidence: float
    # Retry counters — intentionally plain int (not reducers) so nodes control
    # them explicitly. quality_retry_count tracks listing_writer retries (max 1).
    # clarification_count tracks clarification rounds (max 3 per spec).
    quality_retry_count: int
    clarification_count: int

    # Item identification (populated by image_analysis / agent_reasoning)
    item_description: NotRequired[str]
    item_type: NotRequired[str]
    brand: NotRequired[str | None]
    model_name: NotRequired[str | None]
    size: NotRequired[str | None]
    color: NotRequired[str | None]
    condition: NotRequired[str]  # "New" | "Excellent" | "Good" | "Fair" | "Poor"
    condition_notes: NotRequired[str | None]
    accessories_included: NotRequired[list[str]]

    # Images
    image_analysis_raw: NotRequired[dict | None]

    # Price research
    ebay_price_stats: NotRequired[PriceStats | None]
    vinted_price_stats: NotRequired[PriceStats | None]
    ebay_query_used: NotRequired[str | None]
    vinted_query_used: NotRequired[str | None]
    # Per-scraper error fields to avoid fan-in collision when both run in parallel
    ebay_error: NotRequired[str | None]
    vinted_error: NotRequired[str | None]

    # Decision
    suggested_price: NotRequired[float | None]
    preferred_platform: NotRequired[str | None]  # "ebay" | "vinted" | "both"
    platform_reasoning: NotRequired[str | None]

    # Output
    listing_draft: NotRequired[ListingDraft | None]
    quality_passed: NotRequired[bool]
    quality_issues: NotRequired[list[str]]

    # Control flow
    clarification_question: NotRequired[str | None]
    error_state: NotRequired[str | None]
