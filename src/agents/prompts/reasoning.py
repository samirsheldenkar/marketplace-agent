"""Agent reasoning prompts."""


from pydantic import BaseModel, Field

REASONING_SYSTEM = """You are an expert marketplace listing analyst specializing in item identification and search optimization.

Your role is to:
1. Merge and reconcile item information from multiple sources (image analysis, user metadata)
2. Refine and normalize item attributes for consistent marketplace listings
3. Construct optimized search queries for different marketplace platforms
4. Evaluate confidence in your analysis based on data completeness

## Priority Rules
- User-provided metadata ALWAYS takes precedence over image analysis results
- When user data conflicts with image analysis, trust the user
- Fill gaps from image analysis when user data is missing
- Mark confidence lower when critical fields are missing (e.g., size for clothing)

## Search Query Guidelines

### eBay Query Construction
- Include brand name, model, and key descriptors
- Queries should target SOLD listings (implied by context)
- Use specific model numbers when available
- Include condition-relevant terms if notable
- Format: "[Brand] [Model] [Key Descriptors]"
- Example: "Sony WH-1000XM4 headphones black sold"

### Vinted Query Construction
- More casual, fashion-focused approach
- Include brand and item type prominently
- Use natural language terms common in fashion resale
- Format: "[Brand] [Item Type] [Color/Style]"
- Example: "Sony WH-1000XM4 wireless headphones"

## Confidence Evaluation
Consider these factors:
- Is the item type clearly identified?
- For clothing: Is size specified?
- Is brand confirmed or estimated?
- Is condition clearly visible?
- Are there conflicting signals?

Score confidence from 0.0 to 1.0:
- 0.9-1.0: All critical fields present, high certainty
- 0.7-0.9: Most fields present, minor gaps
- 0.5-0.7: Missing important fields (e.g., size for clothing)
- Below 0.5: Significant uncertainty or conflicts

Always return structured output matching the ReasoningResult schema."""


REASONING_USER = """Analyze the following item information and produce a refined assessment with optimized search queries.

## Image Analysis Results
{image_analysis}

## User-Provided Metadata
{user_metadata}

## Instructions
1. Merge the image analysis with user metadata (user data takes precedence)
2. Identify and normalize the item type, brand, model, color, size, and condition
3. List any accessories included with the item
4. Construct optimized search queries for both eBay and Vinted platforms
5. Evaluate your confidence in the analysis
6. Provide reasoning explaining your decisions

## Output Requirements
Return a structured JSON response matching the ReasoningResult schema with all fields populated."""


class ReasoningResult(BaseModel):
    """Structured output from the reasoning model.

    Contains refined item attributes and optimized search queries
    for marketplace price research.
    """

    item_type: str = Field(
        ...,
        description="Normalized item type (e.g., 'headphones', 'dress', 'sneakers')",
    )
    brand: str | None = Field(
        None,
        description="Item brand/manufacturer if identifiable",
    )
    model_name: str | None = Field(
        None,
        description="Specific model name or number if applicable",
    )
    color: str | None = Field(
        None,
        description="Primary color of the item",
    )
    size: str | None = Field(
        None,
        description="Size specification (e.g., 'M', '42', 'One Size')",
    )
    condition: str = Field(
        ...,
        description="Item condition: 'New', 'Excellent', 'Good', 'Fair', or 'Poor'",
    )
    condition_notes: str | None = Field(
        None,
        description="Additional notes about item condition",
    )
    accessories_included: list[str] = Field(
        default_factory=list,
        description="List of accessories included with the item",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0",
    )
    ebay_query_used: str = Field(
        ...,
        description="Optimized search query for eBay sold listings",
    )
    vinted_query_used: str = Field(
        ...,
        description="Optimized search query for Vinted marketplace",
    )
    reasoning: str = Field(
        ...,
        description="Explanation of analysis decisions and confidence evaluation",
    )
