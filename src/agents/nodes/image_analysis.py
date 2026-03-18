"""Image analysis node for item recognition."""

import asyncio
import base64
import logging
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agents.prompts.image_analysis import (
    IMAGE_ANALYSIS_SYSTEM,
    IMAGE_ANALYSIS_USER,
    ImageAnalysisResult,
)
from src.config import get_settings
from src.models.state import ListState

logger = logging.getLogger(__name__)


async def _load_image_as_base64(file_path: str) -> str:
    """Load an image file and return base64-encoded string.

    Args:
        file_path: Path to the image file.

    Returns:
        Base64-encoded string of the image content.

    """
    path = Path(file_path)

    def _read_bytes() -> bytes:
        return path.read_bytes()

    image_bytes = await asyncio.to_thread(_read_bytes)
    return base64.b64encode(image_bytes).decode("utf-8")


def _get_image_media_type(file_path: str) -> str:
    """Determine the media type for an image based on file extension.

    Args:
        file_path: Path to the image file.

    Returns:
        Media type string (e.g., 'image/jpeg', 'image/png').

    """
    extension = Path(file_path).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return media_types.get(extension, "image/jpeg")


async def _build_image_content(file_path: str) -> dict[str, Any]:
    """Build the image content block for vision model input.

    Args:
        file_path: Path to the image file.

    Returns:
        Dictionary with image_url containing base64 data.

    """
    base64_data = await _load_image_as_base64(file_path)
    media_type = _get_image_media_type(file_path)
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{media_type};base64,{base64_data}",
        },
    }


async def image_analysis(state: ListState) -> dict:
    """Analyze item photos using vision model to extract structured attributes.

    This node loads images from the state, encodes them as base64, and sends
    them to a vision model (via LiteLLM) for analysis. The model extracts
    structured information about the item including type, brand, condition,
    and other attributes.

    Args:
        state: Current LangGraph state containing photos and other context.

    Returns:
        Dictionary with fields to update in state:
            - item_type: Identified item type
            - brand: Brand name if identifiable
            - model_name: Model name if identifiable
            - size: Size information
            - color: Primary color(s)
            - condition: Condition assessment
            - condition_notes: Notes about condition
            - confidence: Confidence score (0.0-1.0)
            - accessories_included: List of visible accessories
            - image_analysis_raw: Raw analysis result dict

    """
    settings = get_settings()
    photos = state.get("photos", [])

    if not photos:
        logger.warning("No photos provided for analysis")
        return {
            "item_type": "unknown",
            "brand": None,
            "model_name": None,
            "size": None,
            "color": None,
            "condition": "Good",
            "condition_notes": "No images provided for analysis",
            "confidence": 0.0,
            "accessories_included": [],
            "image_analysis_raw": None,
        }

    # Initialize the vision model
    llm = ChatOpenAI(
        base_url=f"{settings.litellm_url}/v1",
        model=settings.vision_model,
        api_key=settings.litellm_api_key,
        temperature=0.1,
        max_tokens=2048,
    )

    # Configure for structured output
    structured_llm = llm.with_structured_output(ImageAnalysisResult)

    # Build the message content with text and images
    image_paths_str = "\n".join(f"- {path}" for path in photos)
    user_prompt = IMAGE_ANALYSIS_USER.format(image_paths=image_paths_str)

    # Build content blocks: text first, then images
    content: list[Any] = [{"type": "text", "text": user_prompt}]

    for photo_path in photos:
        try:
            image_content = await _build_image_content(photo_path)
            content.append(image_content)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Failed to load image for analysis",
                path=photo_path,
            )
            continue

    try:
        # Call the vision model
        messages = [
            SystemMessage(content=IMAGE_ANALYSIS_SYSTEM),
            HumanMessage(content=content),
        ]

        result = await structured_llm.ainvoke(messages)

        # Extract structured result
        analysis_dict = result.model_dump()

        logger.info(
            "Image analysis completed",
            item_type=result.item_type,
            brand=result.brand,
            confidence=result.confidence,
        )

        return {
            "item_type": result.item_type,
            "brand": result.brand,
            "model_name": result.model_name,
            "size": result.size,
            "color": result.color,
            "condition": result.condition,
            "condition_notes": result.condition_notes,
            "confidence": result.confidence,
            "accessories_included": result.accessories_included,
            "image_analysis_raw": analysis_dict,
        }

    except Exception as e:
        logger.exception(
            "Image analysis failed",
            photos_count=len(photos),
        )

        # Return graceful fallback with zero confidence
        return {
            "item_type": "unknown",
            "brand": None,
            "model_name": None,
            "size": None,
            "color": None,
            "condition": "Good",
            "condition_notes": f"Analysis failed: {e!s}",
            "confidence": 0.0,
            "accessories_included": [],
            "image_analysis_raw": {"error": str(e)},
        }
