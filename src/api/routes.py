"""FastAPI route definitions."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    ClarificationRequest,
    ClarificationResponse,
    CreateListingResponse,
    GetListingResponse,
)
from src.config import Settings, get_settings
from src.db.session import get_db

router = APIRouter()


@router.post("/listing", response_model=CreateListingResponse)  # noqa: FAST001
async def create_listing(
    _request: Request,
    _images: list[UploadFile] = File(...),  # noqa: B008, FAST002
    _brand: str | None = Form(None),  # noqa: FAST002
    _size: str | None = Form(None),  # noqa: FAST002
    _color: str | None = Form(None),  # noqa: FAST002
    _notes: str | None = Form(None),  # noqa: FAST002
    _fast_sale: bool = Form(True, description="Apply discount pricing for quick sale"),  # noqa: FAST002, FBT001, FBT003
    _settings: Settings = Depends(get_settings),  # noqa: B008, FAST002
    _db: AsyncSession = Depends(get_db),  # noqa: B008, FAST002
) -> CreateListingResponse:
    """Create a new listing from uploaded images."""
    # TODO(samir): Implement listing creation logic  # noqa: TD003
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/listing/{listing_id}/clarify", response_model=ClarificationResponse)  # noqa: FAST001
async def submit_clarification(
    _listing_id: UUID,
    _clarification: ClarificationRequest,
    _settings: Settings = Depends(get_settings),  # noqa: B008, FAST002
    _db: AsyncSession = Depends(get_db),  # noqa: B008, FAST002
) -> ClarificationResponse:
    """Submit clarification answer for a listing."""
    # TODO(samir): Implement clarification logic  # noqa: TD003
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/listing/{listing_id}", response_model=GetListingResponse)  # noqa: FAST001
async def get_listing(
    _listing_id: UUID,
    _db: AsyncSession = Depends(get_db),  # noqa: B008, FAST002
) -> GetListingResponse:
    """Get a listing by ID."""
    # TODO(samir): Implement get listing logic  # noqa: TD003
    raise HTTPException(status_code=501, detail="Not implemented")
