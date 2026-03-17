"""Image service for upload, validation, and storage."""

import os
import uuid
from pathlib import Path
from typing import List

from fastapi import UploadFile

from src.config import Settings
from src.exceptions import ImageProcessingError, ValidationError


class ImageService:
    """Service for handling image uploads and storage."""

    def __init__(self, settings: Settings):
        """Initialize image service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.storage_path = Path(settings.image_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def validate_image(self, file: UploadFile) -> None:
        """Validate image file.

        Args:
            file: Uploaded file

        Raises:
            ValidationError: If file is invalid
        """
        # Check file extension
        ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if ext not in self.settings.allowed_image_formats:
            raise ValidationError(
                f"Invalid image format: {ext}. "
                f"Allowed: {', '.join(self.settings.allowed_image_formats)}"
            )

        # Read content for size check
        content = await file.read()
        await file.seek(0)  # Reset for later use

        max_bytes = self.settings.max_image_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise ValidationError(
                f"Image too large: {len(content)} bytes. "
                f"Max: {max_bytes} bytes"
            )

    async def store_images(
        self,
        listing_id: str,
        files: List[UploadFile],
    ) -> List[str]:
        """Store uploaded images.

        Args:
            listing_id: Listing ID for directory organization
            files: List of uploaded files

        Returns:
            List of stored file paths

        Raises:
            ImageProcessingError: If storage fails
        """
        # Create listing-specific directory
        listing_dir = self.storage_path / listing_id
        listing_dir.mkdir(parents=True, exist_ok=True)

        stored_paths = []

        for file in files:
            try:
                # Generate unique filename
                ext = (
                    file.filename.split(".")[-1].lower()
                    if "." in file.filename
                    else "jpg"
                )
                filename = f"{uuid.uuid4()}.{ext}"
                file_path = listing_dir / filename

                # Read and save file
                content = await file.read()
                with open(file_path, "wb") as f:
                    f.write(content)

                stored_paths.append(str(file_path))

            except Exception as e:
                raise ImageProcessingError(f"Failed to store image: {str(e)}")

        return stored_paths
