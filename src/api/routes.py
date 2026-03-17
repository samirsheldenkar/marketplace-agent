"""FastAPI route definitions."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    ClarificationRequest,
    ClarificationResponse,
    CreateListingRequest,
    CreateListingResponse,
    GetListingResponse,
    HealthResponse,
)
from src.config import Settings, get_settings
from src.db.session import get_db

router = APIRouter()


@router.post("/listing", response_model=CreateListingResponse)
async def create_listing(
    request: Request,
    images: List[UploadFile] = File(...),
    brand: Optional[str] = Form(None),
    size: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Create a new listing from uploaded images."""
    # TODO: Implement listing creation logic
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/listing/{listing_id}/clarify", response_model=ClarificationResponse)
async def submit_clarification(
    listing_id: UUID,
    clarification: ClarificationRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Submit clarification answer for a listing."""
    # TODO: Implement clarification logic
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/listing/{listing_id}", response_model=GetListingResponse)
async def get_listing(
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a listing by ID."""
    # TODO: Implement get listing logic
    raise HTTPException(status_code=501, detail="Not implemented")
