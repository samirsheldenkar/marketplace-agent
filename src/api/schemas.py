"""Pydantic schemas for API request/response validation."""

from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PriceStats(BaseModel):
    """Price statistics schema."""

    num_listings: int
    avg_price: float
    median_price: float
    min_price: float
    max_price: float
    items: List[dict]


class ListingDraft(BaseModel):
    """Generated listing content schema."""

    title: str
    description: str
    category_suggestions: List[str]
    shipping_suggestion: str
    returns_policy: str


class ItemInfo(BaseModel):
    """Item identification info."""

    type: str
    brand: Optional[str] = None
    model: Optional[str] = None
    condition: str
    confidence: float


class PricingInfo(BaseModel):
    """Pricing information schema."""

    suggested_price: float
    currency: str = "GBP"
    preferred_platform: str
    platform_reasoning: str
    ebay_stats: Optional[PriceStats] = None
    vinted_stats: Optional[PriceStats] = None


class CreateListingRequest(BaseModel):
    """Request schema for creating a listing."""

    brand: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None


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
    clarification_question: Optional[str] = None
    item: Optional[ItemInfo] = None
    pricing: Optional[PricingInfo] = None
    listing_draft: Optional[ListingDraft] = None


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
