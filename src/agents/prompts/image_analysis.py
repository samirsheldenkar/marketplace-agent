"""Image analysis prompts for vision model (GPT-4o via LiteLLM)."""

from pydantic import BaseModel, Field

IMAGE_ANALYSIS_SYSTEM = """You are an expert item analyzer for marketplace listings. Your role is to carefully examine product photos and extract detailed, accurate information about items for sale.

You must analyze all provided images thoroughly and output a structured JSON response that matches the required schema exactly.

Your analysis should be:
1. Accurate - Only report what you can clearly see in the images
2. Detailed - Capture brand, model, color, size, and condition details
3. Honest - Note uncertainty and provide confidence scores appropriately
4. Complete - List all visible accessories and notable features

Output Format:
Return a valid JSON object with the following structure:
{
  "item_type": "string (e.g., 'headphones', 'dress', 'laptop')",
  "brand": "string or null",
  "model_name": "string or null",
  "color": "string or null",
  "size": "string or null",
  "condition": "New | Excellent | Good | Fair | Poor",
  "condition_notes": "string or null",
  "accessories_included": ["list of visible accessories"],
  "confidence": 0.0 to 1.0,
  "reasoning": "string explaining your analysis"
}

Condition Assessment Guidelines:
- New: Unused, original packaging, no signs of wear
- Excellent: Like new, minimal signs of use, no visible damage
- Good: Normal wear consistent with age, minor cosmetic issues
- Fair: Noticeable wear, some damage or defects visible
- Poor: Significant damage, missing parts, or heavy wear

Always provide a confidence score between 0.0 and 1.0 reflecting how certain you are about your analysis.
Include reasoning that explains your assessment and any limitations based on image quality or angles."""

IMAGE_ANALYSIS_USER = """Please analyze the following item images and provide a detailed assessment.

Images to analyze:
{image_paths}

Examine each image carefully and provide:
1. The type of item (be specific)
2. Brand and model if identifiable
3. Color and size if applicable
4. Condition assessment with notes on any visible wear or damage
5. Any accessories visible in the photos
6. Your confidence level and reasoning

Return your analysis as structured JSON matching the required schema."""


class ImageAnalysisResult(BaseModel):
    """Structured output from image analysis.

    Contains all extracted information about an item from photo analysis.
    """

    item_type: str = Field(
        ...,
        description="The type of item identified (e.g., 'headphones', 'dress', 'laptop')",
    )
    brand: str | None = Field(
        None,
        description="Brand name if identifiable from logos, labels, or design",
    )
    model_name: str | None = Field(
        None,
        description="Specific model name or number if identifiable",
    )
    color: str | None = Field(
        None,
        description="Primary color(s) of the item",
    )
    size: str | None = Field(
        None,
        description="Size information (e.g., 'M', '42', '15 inch')",
    )
    condition: str = Field(
        ...,
        description="Condition assessment: New, Excellent, Good, Fair, or Poor",
    )
    condition_notes: str | None = Field(
        None,
        description="Additional notes about condition (wear, damage, defects)",
    )
    accessories_included: list[str] = Field(
        default_factory=list,
        description="List of accessories visible in photos",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the analysis (0.0 to 1.0)",
    )
    reasoning: str = Field(
        ...,
        description="Explanation of the analysis and any limitations",
    )
