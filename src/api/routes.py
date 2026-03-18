"""FastAPI route definitions."""

import uuid
from typing import Any
from uuid import UUID

import httpx
import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from src.agents.graph import agent_graph
from src.api.dependencies import verify_api_key
from src.api.metrics import (
    record_clarification_round,
    record_listing_status,
    timed_listing_creation,
)
from src.api.schemas import (
    ClarificationRequest,
    ClarificationResponse,
    CreateListingResponse,
    GetListingResponse,
    HealthResponse,
    ItemInfo,
    ListingDraft,
    PriceStats,
    PricingInfo,
)
from src.config import Settings, get_settings
from src.db.repositories import ListingRepository
from src.db.session import get_db
from src.exceptions import ImageProcessingError, LLMError, ScraperError, ValidationError
from src.models.database import ListingStatus
from src.models.state import ListState
from src.services.image_service import ImageService

logger = structlog.get_logger()

router = APIRouter()


HTTP_OK = 200


def _state_to_item_info(state: dict[str, Any]) -> ItemInfo:
    """Convert state to ItemInfo schema.

    Args:
        state: Agent state dictionary.

    Returns:
        ItemInfo instance.

    """
    return ItemInfo(
        type=state.get("item_type", "unknown"),
        brand=state.get("brand"),
        model=state.get("model_name"),
        condition=state.get("condition", "unknown"),
        confidence=state.get("confidence", 0.0),
    )


def _state_to_pricing_info(state: dict[str, Any]) -> PricingInfo:
    """Convert state to PricingInfo schema.

    Args:
        state: Agent state dictionary.

    Returns:
        PricingInfo instance.

    """
    ebay_stats = None
    if state.get("ebay_price_stats"):
        eps = state["ebay_price_stats"]
        ebay_stats = PriceStats(
            num_listings=eps.get("num_listings", 0),
            avg_price=eps.get("avg_price", 0.0),
            median_price=eps.get("median_price", 0.0),
            min_price=eps.get("min_price", 0.0),
            max_price=eps.get("max_price", 0.0),
            items=eps.get("items", []),
        )

    vinted_stats = None
    if state.get("vinted_price_stats"):
        vps = state["vinted_price_stats"]
        vinted_stats = PriceStats(
            num_listings=vps.get("num_listings", 0),
            avg_price=vps.get("avg_price", 0.0),
            median_price=vps.get("median_price", 0.0),
            min_price=vps.get("min_price", 0.0),
            max_price=vps.get("max_price", 0.0),
            items=vps.get("items", []),
        )

    return PricingInfo(
        suggested_price=state.get("suggested_price", 0.0),
        currency="GBP",
        preferred_platform=state.get("preferred_platform", "ebay"),
        platform_reasoning=state.get("platform_reasoning", ""),
        ebay_stats=ebay_stats,
        vinted_stats=vinted_stats,
    )


def _state_to_listing_draft(state: dict[str, Any]) -> ListingDraft:
    """Convert state to ListingDraft schema.

    Args:
        state: Agent state dictionary.

    Returns:
        ListingDraft instance.

    """
    draft = state.get("listing_draft", {})
    return ListingDraft(
        title=draft.get("title", ""),
        description=draft.get("description", ""),
        category_suggestions=draft.get("category_suggestions", []),
        shipping_suggestion=draft.get("shipping_suggestion", ""),
        returns_policy=draft.get("returns_policy", ""),
    )


def _state_to_listing_response(
    listing: Any, state: dict[str, Any]
) -> CreateListingResponse:
    """Convert state to API response.

    Args:
        listing: Listing database model.
        state: Agent state dictionary.

    Returns:
        CreateListingResponse instance.

    """
    return CreateListingResponse(
        listing_id=listing.id,
        status=listing.status.value,
        item=_state_to_item_info(state),
        pricing=_state_to_pricing_info(state),
        listing_draft=_state_to_listing_draft(state),
    )


def _state_to_clarification_response(
    listing: Any, state: dict[str, Any]
) -> ClarificationResponse:
    """Convert state to clarification response.

    Args:
        listing: Listing database model.
        state: Agent state dictionary.

    Returns:
        ClarificationResponse instance.

    """
    return ClarificationResponse(
        listing_id=listing.id,
        status=listing.status.value,
        clarification_question=state.get("clarification_question"),
        item=_state_to_item_info(state) if state.get("item_type") else None,
        pricing=_state_to_pricing_info(state) if state.get("suggested_price") else None,
        listing_draft=_state_to_listing_draft(state)
        if state.get("listing_draft")
        else None,
    )


async def _run_agent_graph(
    db: AsyncSession,
    listing_id: UUID,
    state: ListState,
) -> ListState:
    """Run the agent graph and update listing status.

    Args:
        db: Database session.
        listing_id: UUID of the listing.
        state: Initial agent state.

    Returns:
        Updated agent state.

    Raises:
        HTTPException: If agent execution fails.

    """
    listing_repo = ListingRepository(db)

    try:
        # Update status to processing
        await listing_repo.update_status(listing_id, ListingStatus.PROCESSING)

        # Run the agent graph
        result = await agent_graph.ainvoke(state)

        # Determine final status based on state
        needs_clarification = result.get("needs_clarification", False)
        has_error = result.get("error_state") is not None

        if has_error:
            new_status = ListingStatus.FAILED
        elif needs_clarification:
            new_status = ListingStatus.CLARIFICATION
        else:
            new_status = ListingStatus.COMPLETED

        # Update listing with results
        await listing_repo.update(
            listing_id,
            status=new_status,
            item_type=result.get("item_type"),
            brand=result.get("brand"),
            model_name=result.get("model_name"),
            condition=result.get("condition"),
            confidence=result.get("confidence"),
            suggested_price=result.get("suggested_price"),
            preferred_platform=result.get("preferred_platform"),
            platform_reasoning=result.get("platform_reasoning"),
            raw_state=dict(result),
        )

        # Update listing draft if available
        if result.get("listing_draft"):
            draft = result["listing_draft"]
            await listing_repo.update(
                listing_id,
                title=draft.get("title"),
                description=draft.get("description"),
                listing_draft=draft,
            )

        await db.commit()
        return result

    except LLMError as e:
        logger.exception("LLM error during agent execution")
        await listing_repo.update_status(listing_id, ListingStatus.FAILED)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM gateway unavailable",
        ) from e
    except ScraperError as e:
        logger.exception("Scraper error during agent execution")
        await listing_repo.update_status(listing_id, ListingStatus.FAILED)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Marketplace scrapers unavailable",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error during agent execution")
        await listing_repo.update_status(listing_id, ListingStatus.FAILED)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during listing creation",
        ) from e


@router.post("/listing", response_model=CreateListingResponse)
async def create_listing(
    _request: Request,
    images: list[UploadFile] = File(...),
    brand: str | None = Form(None),
    size: str | None = Form(None),
    color: str | None = Form(None),
    notes: str | None = Form(None),
    fast_sale: bool = Form(True, description="Apply discount pricing for quick sale"),
    _api_key: str = Depends(verify_api_key),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> CreateListingResponse:
    """Create a new listing from uploaded images.

    Args:
        _request: FastAPI request object (unused).
        images: List of uploaded image files (1-10 images).
        brand: Optional brand name hint.
        size: Optional size hint.
        color: Optional color hint.
        notes: Optional condition notes.
        fast_sale: Whether to apply discount pricing for quick sale.
        _api_key: Validated API key.
        settings: Application settings.
        db: Database session.

    Returns:
        CreateListingResponse with listing details.

    Raises:
        HTTPException: If validation fails or processing errors occur.

    """
    # Validate image count
    if len(images) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one image is required",
        )
    if len(images) > settings.max_images_per_listing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.max_images_per_listing} images allowed",
        )

    # Initialize services
    image_service = ImageService(settings)
    listing_repo = ListingRepository(db)

    # Validate all images
    for image in images:
        try:
            await image_service.validate_image(image)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

    # Generate listing ID for image storage
    listing_id = uuid.uuid4()

    # Store images
    try:
        image_paths = await image_service.store_images(str(listing_id), images)
    except ImageProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store images: {e!s}",
        ) from e

    # Build initial state
    initial_state: ListState = {
        "run_id": str(listing_id),
        "messages": [],
        "photos": image_paths,
        "brand": brand,
        "size": size,
        "color": color,
        "condition_notes": notes,
        "fast_sale": fast_sale,
        "confidence": 0.0,
        "needs_clarification": False,
        "retry_count": 0,
    }

    # Create listing record
    listing = await listing_repo.create(
        image_paths=image_paths,
        brand=brand,
        size=size,
        color=color,
        condition_notes=notes,
    )

    await db.commit()

    logger.info(
        "Created listing",
        listing_id=str(listing.id),
        image_count=len(images),
    )

    # Run agent graph with timing
    with timed_listing_creation():
        result_state = await _run_agent_graph(db, listing.id, initial_state)

    # Record metrics
    record_listing_status(listing.status.value)

    # Return appropriate response based on status
    if listing.status == ListingStatus.COMPLETED:
        return _state_to_listing_response(listing, dict(result_state))
    if listing.status == ListingStatus.CLARIFICATION:
        # 202 Accepted — indicates the caller should submit a clarification answer
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "listing_id": str(listing.id),
                "status": "clarification",
                "clarification_question": result_state.get("clarification_question"),
            },
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Listing creation failed",
    )


@router.post("/listing/{listing_id}/clarify", response_model=ClarificationResponse)
async def submit_clarification(
    listing_id: UUID,
    clarification: ClarificationRequest,
    _api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> ClarificationResponse:
    """Submit clarification answer for a listing.

    Args:
        listing_id: UUID of the listing.
        clarification: Clarification request with answer.
        _api_key: Validated API key.
        db: Database session.

    Returns:
        ClarificationResponse with updated listing status.

    Raises:
        HTTPException: If listing not found or processing fails.

    """
    listing_repo = ListingRepository(db)

    # Get existing listing
    listing = await listing_repo.get_by_id(listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found",
        )

    # Check listing is in clarification state
    if listing.status != ListingStatus.CLARIFICATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Listing is not awaiting clarification "
                f"(status: {listing.status.value})"
            ),
        )

    # Retrieve raw state
    if not listing.raw_state:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Listing state not found",
        )

    # Update state with clarification answer
    state: ListState = listing.raw_state.copy()
    state["messages"] = [
        *state.get("messages", []),
        {"role": "user", "content": clarification.answer},
    ]
    state["needs_clarification"] = False

    # Record clarification round
    record_clarification_round()

    # Re-run agent graph
    result_state = await _run_agent_graph(db, listing_id, state)

    # Refresh listing from database
    listing = await listing_repo.get_by_id(listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve updated listing",
        )

    # Record final status
    record_listing_status(listing.status.value)

    # Return response based on new status
    if listing.status == ListingStatus.COMPLETED:
        # Return clarification response with full data
        return _state_to_clarification_response(listing, dict(result_state))
    if listing.status == ListingStatus.CLARIFICATION:
        # Still needs clarification
        return _state_to_clarification_response(listing, dict(result_state))
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Clarification processing failed",
    )


@router.get("/listing/{listing_id}", response_model=GetListingResponse)
async def get_listing(
    listing_id: UUID,
    _api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> GetListingResponse:
    """Get a listing by ID.

    Args:
        listing_id: UUID of the listing.
        _api_key: Validated API key.
        db: Database session.

    Returns:
        GetListingResponse with listing details.

    Raises:
        HTTPException: If listing not found.

    """
    listing_repo = ListingRepository(db)

    listing = await listing_repo.get_by_id(listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found",
        )

    # Build response from listing data
    item_info = ItemInfo(
        type=listing.item_type or "unknown",
        brand=listing.brand,
        model=listing.model_name,
        condition=listing.condition or "unknown",
        confidence=listing.confidence or 0.0,
    )

    pricing_info = PricingInfo(
        suggested_price=float(listing.suggested_price)
        if listing.suggested_price
        else 0.0,
        currency="GBP",
        preferred_platform=listing.preferred_platform or "ebay",
        platform_reasoning=listing.platform_reasoning or "",
    )

    # Get listing draft from raw_state if available
    draft_data = {}
    if listing.raw_state and listing.raw_state.get("listing_draft"):
        draft_data = listing.raw_state["listing_draft"]

    listing_draft = ListingDraft(
        title=listing.title or draft_data.get("title", ""),
        description=listing.description or draft_data.get("description", ""),
        category_suggestions=draft_data.get("category_suggestions", []),
        shipping_suggestion=draft_data.get("shipping_suggestion", ""),
        returns_policy=draft_data.get("returns_policy", ""),
    )

    return GetListingResponse(
        listing_id=listing.id,
        status=listing.status.value,
        item=item_info,
        pricing=pricing_info,
        listing_draft=listing_draft,
    )


@router.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics.

    Returns:
        Response with Prometheus metrics.

    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """Health check endpoint.

    Verifies database connectivity and LiteLLM gateway availability.

    Args:
        settings: Application settings.
        db: Database session.

    Returns:
        HealthResponse with service status.

    """
    services: dict[str, Any] = {}

    # Check database connectivity
    try:
        # Execute a simple query to verify connection
        await db.execute(text("SELECT 1"))
        services["database"] = {"status": "healthy"}
    except (OSError, RuntimeError) as e:
        logger.warning("Database health check failed", extra={"error": str(e)})
        services["database"] = {"status": "unhealthy", "error": str(e)}

    # Check LiteLLM gateway availability
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.litellm_url}/health")
            if response.status_code == HTTP_OK:
                services["litellm"] = {"status": "healthy"}
            else:
                services["litellm"] = {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                }
    except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning("LiteLLM health check failed", extra={"error": str(e)})
        services["litellm"] = {"status": "unhealthy", "error": str(e)}

    # Determine overall status
    all_healthy = all(svc.get("status") == "healthy" for svc in services.values())
    overall_status = "healthy" if all_healthy else "degraded"

    return HealthResponse(
        status=overall_status,
        services=services,
        version="1.0.0",
    )
