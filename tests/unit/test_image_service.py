"""Unit tests for image service."""

import os
from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi import UploadFile

from src.exceptions import ImageProcessingError, ValidationError
from src.services.image_service import ImageService


class TestImageService:
    """Test ImageService functionality."""

    @pytest.fixture
    def service(self, test_settings):
        """Create image service instance."""
        return ImageService(test_settings)

    @pytest.mark.asyncio
    async def test_validate_image_valid_format_jpeg(self, service):
        """Test validating an image with valid JPEG format."""
        # Arrange
        content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"fake" * 100
        file = BytesIO(content)
        upload_file = UploadFile(filename="test.jpg", file=file)

        # Act & Assert - Should not raise
        await service.validate_image(upload_file)

    @pytest.mark.asyncio
    async def test_validate_image_valid_format_png(self, service):
        """Test validating an image with valid PNG format."""
        # Arrange
        content = b"\x89PNG\r\n\x1a\n" + b"fake" * 100
        file = BytesIO(content)
        upload_file = UploadFile(filename="test.png", file=file)

        # Act & Assert - Should not raise
        await service.validate_image(upload_file)

    @pytest.mark.asyncio
    async def test_validate_image_valid_format_webp(self, service):
        """Test validating an image with valid WebP format."""
        # Arrange
        content = b"RIFF" + b"\x00\x00\x00\x00WEBP" + b"fake" * 100
        file = BytesIO(content)
        upload_file = UploadFile(filename="test.webp", file=file)

        # Act & Assert - Should not raise
        await service.validate_image(upload_file)

    @pytest.mark.asyncio
    async def test_validate_image_invalid_format(self, service):
        """Test validating an image with invalid format."""
        # Arrange
        file = BytesIO(b"invalid content")
        upload_file = UploadFile(filename="test.txt", file=file)

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid image format"):
            await service.validate_image(upload_file)

    @pytest.mark.asyncio
    async def test_validate_image_no_extension(self, service):
        """Test validating an image without file extension."""
        # Arrange
        file = BytesIO(b"some content")
        upload_file = UploadFile(filename="testfile", file=file)

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid image format"):
            await service.validate_image(upload_file)

    @pytest.mark.asyncio
    async def test_validate_image_too_large(self, service, test_settings):
        """Test validating an image that exceeds size limit."""
        # Arrange - Create oversized file (1 byte over limit)
        max_bytes = test_settings.max_image_size_mb * 1024 * 1024
        large_content = b"x" * (max_bytes + 1)
        file = BytesIO(large_content)
        upload_file = UploadFile(filename="test.jpg", file=file)

        # Act & Assert
        with pytest.raises(ValidationError, match="too large"):
            await service.validate_image(upload_file)

    @pytest.mark.asyncio
    async def test_validate_image_at_size_limit(self, service, test_settings):
        """Test validating an image at exactly the size limit."""
        # Arrange - Create file at exactly the limit
        max_bytes = test_settings.max_image_size_mb * 1024 * 1024
        content = b"\xff\xd8\xff\xe0" + b"x" * (max_bytes - 4)
        file = BytesIO(content)
        upload_file = UploadFile(filename="test.jpg", file=file)

        # Act & Assert - Should not raise
        await service.validate_image(upload_file)

    @pytest.mark.asyncio
    async def test_store_images_success(self, service, tmp_path):
        """Test successfully storing images."""
        # Arrange
        listing_id = "test-listing-123"

        # Create mock files
        files = []
        for i in range(3):
            content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + f"image{i}".encode()
            file = BytesIO(content)
            upload_file = UploadFile(filename=f"test{i}.jpg", file=file)
            files.append(upload_file)

        # Act
        paths = await service.store_images(listing_id, files)

        # Assert
        assert len(paths) == 3
        for path in paths:
            assert listing_id in path
            assert path.endswith(".jpg")
            assert os.path.exists(path)

    @pytest.mark.asyncio
    async def test_store_images_creates_directory(self, service):
        """Test that store_images creates listing directory if it doesn't exist."""
        # Arrange
        listing_id = "new-listing-dir"
        content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"test"
        file = BytesIO(content)
        upload_file = UploadFile(filename="test.jpg", file=file)

        # Act
        paths = await service.store_images(listing_id, [upload_file])

        # Assert
        assert len(paths) == 1
        assert listing_id in paths[0]
        assert os.path.exists(os.path.dirname(paths[0]))

    @pytest.mark.asyncio
    async def test_store_images_different_extensions(self, service):
        """Test storing images with different file extensions."""
        # Arrange
        listing_id = "test-extensions"

        # Create files with different extensions
        files = [
            UploadFile(
                filename="test.jpg",
                file=BytesIO(b"\xff\xd8\xff\xe0" + b"jpeg content"),
            ),
            UploadFile(
                filename="test.png",
                file=BytesIO(b"\x89PNG\r\n\x1a\n" + b"png content"),
            ),
            UploadFile(
                filename="test.webp",
                file=BytesIO(b"RIFF\x00\x00\x00\x00WEBP" + b"webp content"),
            ),
        ]

        # Act
        paths = await service.store_images(listing_id, files)

        # Assert
        assert len(paths) == 3
        extensions = [p.split(".")[-1] for p in paths]
        assert "jpg" in extensions
        assert "png" in extensions
        assert "webp" in extensions

    @pytest.mark.asyncio
    async def test_store_images_empty_list(self, service):
        """Test storing empty list of images."""
        # Arrange
        listing_id = "empty-listing"

        # Act
        paths = await service.store_images(listing_id, [])

        # Assert
        assert len(paths) == 0

    @pytest.mark.asyncio
    async def test_store_images_file_without_extension(self, service):
        """Test storing image file without extension defaults to jpg."""
        # Arrange
        listing_id = "no-extension"
        file = BytesIO(b"image content")
        upload_file = UploadFile(filename="testfile", file=file)

        # Act
        paths = await service.store_images(listing_id, [upload_file])

        # Assert
        assert len(paths) == 1
        assert paths[0].endswith(".jpg")

    @pytest.mark.asyncio
    async def test_store_images_unique_filenames(self, service):
        """Test that stored images have unique filenames."""
        # Arrange
        listing_id = "unique-names"
        files = [
            UploadFile(filename="test.jpg", file=BytesIO(b"content1")),
            UploadFile(filename="test.jpg", file=BytesIO(b"content2")),
            UploadFile(filename="test.jpg", file=BytesIO(b"content3")),
        ]

        # Act
        paths = await service.store_images(listing_id, files)

        # Assert
        assert len(paths) == 3
        # Extract filenames from paths
        filenames = [os.path.basename(p) for p in paths]
        # All filenames should be unique
        assert len(set(filenames)) == 3

    @pytest.mark.asyncio
    async def test_store_images_handles_special_characters_in_listing_id(self, service):
        """Test storing images with special characters in listing ID."""
        # Arrange
        listing_id = "listing-with-special_chars.123"
        file = BytesIO(b"content")
        upload_file = UploadFile(filename="test.jpg", file=file)

        # Act
        paths = await service.store_images(listing_id, [upload_file])

        # Assert
        assert len(paths) == 1
        assert os.path.exists(paths[0])

    @pytest.mark.asyncio
    async def test_validate_image_resets_file_position(self, service):
        """Test that validate_image resets file position after reading."""
        # Arrange
        content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"fake" * 100
        file = BytesIO(content)
        upload_file = UploadFile(filename="test.jpg", file=file)

        # Act
        await service.validate_image(upload_file)

        # Assert - File position should be reset to 0
        assert upload_file.file.tell() == 0

    @pytest.mark.asyncio
    async def test_store_images_preserves_content(self, service):
        """Test that stored images preserve original content."""
        # Arrange
        listing_id = "content-test"
        original_content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"unique content here"
        file = BytesIO(original_content)
        upload_file = UploadFile(filename="test.jpg", file=file)

        # Act
        paths = await service.store_images(listing_id, [upload_file])

        # Assert
        assert len(paths) == 1
        with open(paths[0], "rb") as f:
            stored_content = f.read()
        assert stored_content == original_content


class TestImageServiceEdgeCases:
    """Test edge cases and error handling for ImageService."""

    @pytest.fixture
    def service(self, test_settings):
        """Create image service instance."""
        return ImageService(test_settings)

    @pytest.mark.asyncio
    async def test_validate_image_case_insensitive_extension(self, service):
        """Test that image format validation is case insensitive."""
        # Arrange
        content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"content"
        file = BytesIO(content)
        upload_file = UploadFile(filename="test.JPG", file=file)

        # Act & Assert - Should not raise
        await service.validate_image(upload_file)

    @pytest.mark.asyncio
    async def test_validate_image_jpeg_extension(self, service):
        """Test validating image with .jpeg extension."""
        # Arrange
        content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"content"
        file = BytesIO(content)
        upload_file = UploadFile(filename="test.jpeg", file=file)

        # Act & Assert - Should not raise
        await service.validate_image(upload_file)

    @pytest.mark.asyncio
    async def test_validate_image_gif_format(self, service):
        """Test validating image with GIF format."""
        # Arrange
        content = b"GIF89a" + b"\x00\x00\x00" + b"content"
        file = BytesIO(content)
        upload_file = UploadFile(filename="test.gif", file=file)

        # Act & Assert - Should not raise
        await service.validate_image(upload_file)

    @pytest.mark.asyncio
    async def test_store_images_large_filename(self, service):
        """Test storing image with very long filename."""
        # Arrange
        listing_id = "long-filename-test"
        long_filename = "a" * 200 + ".jpg"
        file = BytesIO(b"content")
        upload_file = UploadFile(filename=long_filename, file=file)

        # Act
        paths = await service.store_images(listing_id, [upload_file])

        # Assert - Should still work, using generated UUID filename
        assert len(paths) == 1
        assert paths[0].endswith(".jpg")

    @pytest.mark.asyncio
    async def test_store_images_unicode_filename(self, service):
        """Test storing image with unicode characters in filename."""
        # Arrange
        listing_id = "unicode-test"
        file = BytesIO(b"content")
        upload_file = UploadFile(filename="test_日本語.jpg", file=file)

        # Act
        paths = await service.store_images(listing_id, [upload_file])

        # Assert
        assert len(paths) == 1
        assert paths[0].endswith(".jpg")

    @pytest.mark.asyncio
    async def test_store_images_multiple_calls_same_listing(self, service):
        """Test storing images in multiple calls for same listing."""
        # Arrange
        listing_id = "multi-call-test"

        # First batch
        files1 = [
            UploadFile(filename="test1.jpg", file=BytesIO(b"content1")),
        ]
        # Second batch
        files2 = [
            UploadFile(filename="test2.jpg", file=BytesIO(b"content2")),
        ]

        # Act
        paths1 = await service.store_images(listing_id, files1)
        paths2 = await service.store_images(listing_id, files2)

        # Assert - Both should succeed
        assert len(paths1) == 1
        assert len(paths2) == 1
        # All files should exist
        assert os.path.exists(paths1[0])
        assert os.path.exists(paths2[0])
