"""Pydantic schemas for API request/response validation."""

from uuid import UUID

from pydantic import BaseModel


class PriceStats(BaseModel):
    """Price statistics schema."""

    num_listings: int
    avg_price: float
    median_price: float
    min_price: float
    max_price: float
    items: list[dict]


class ListingDraft(BaseModel):
    """Generated listing content schema."""

    title: str
    description: str
    category_suggestions: list[str]
    shipping_suggestion: str
    returns_policy: str


class ItemInfo(BaseModel):
    """Item identification info."""

    type: str
    brand: str | None = None
    model: str | None = None
    condition: str
    confidence: float


class PricingInfo(BaseModel):
    """Pricing information schema."""

    suggested_price: float
    currency: str = "GBP"
    preferred_platform: str
    platform_reasoning: str
    ebay_stats: PriceStats | None = None
    vinted_stats: PriceStats | None = None


class CreateListingRequest(BaseModel):
    """Request schema for creating a listing."""

    brand: str | None = None
    size: str | None = None
    color: str | None = None
    notes: str | None = None


class CreateListingResponse(BaseModel):
    """Response schema for created listing."""

    listing_id: UUID
    status: str  # "completed" | "clarification"
    item: ItemInfo
    pricing: PricingInfo
    listing_draft: ListingDraft


class ClarificationRequest(BaseModel):
    """Request schema for clarification submission."""

    answer: str


class ClarificationResponse(BaseModel):
    """Response schema for clarification."""

    listing_id: UUID
    status: str
    clarification_question: str | None = None
    item: ItemInfo | None = None
    pricing: PricingInfo | None = None
    listing_draft: ListingDraft | None = None


class GetListingResponse(BaseModel):
    """Response schema for getting a listing."""

    listing_id: UUID
    status: str
    item: ItemInfo
    pricing: PricingInfo
    listing_draft: ListingDraft


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    services: dict
    version: str
