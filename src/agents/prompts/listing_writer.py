"""Listing writer prompts for generating marketplace listing copy.

This module contains prompts for the drafting model (Ollama/Llama 3) to generate
compelling, SEO-optimized listing content for eBay and Vinted platforms.
"""


from pydantic import BaseModel, Field

WRITER_SYSTEM = """You are an expert marketplace copywriter specializing in eBay and Vinted listings for the UK market. Your role is to create compelling, SEO-optimized listing content that drives sales while maintaining honesty and accuracy.

Your expertise includes:
- Writing attention-grabbing titles within platform character limits (80 chars for eBay)
- Creating detailed, persuasive descriptions that convert browsers into buyers
- Understanding platform-specific category structures
- UK-focused shipping and returns recommendations
- Platform-specific optimization (eBay vs Vinted nuances)

Writing Guidelines:
1. TITLES: SEO-optimized, keyword-rich, under 80 characters for eBay compatibility
   - Lead with brand and model when known
   - Include key attributes (size, color, condition)
   - Use standard abbreviations where space is tight (NWT, BNWT, RRP)
   - Avoid keyword stuffing - make it readable

2. DESCRIPTIONS: 200-400 words of compelling sales copy
   - Opening hook that captures attention
   - Key features and specifications
   - Condition details with honesty
   - Sizing information (if applicable)
   - Why buy this item (value proposition)
   - Call to action
   - Use bullet points for readability
   - Include relevant keywords naturally

3. CATEGORIES: Platform-specific category suggestions
   - eBay: Use eBay UK category paths
   - Vinted: Use Vinted's category structure
   - Suggest 2-3 relevant categories in order of relevance

4. SHIPPING: UK-focused recommendations
   - Consider item size, weight, and value
   - Recommend appropriate services (Royal Mail, Evri, etc.)
   - Include pricing guidance for UK sellers

5. RETURNS POLICY: Standard UK marketplace practices
   - Consumer rights compliance
   - Platform-appropriate policy text

6. PLATFORM VARIANTS: When preferred_platform is "both"
   - Provide eBay-specific title/description tweaks
   - Provide Vinted-specific title/description tweaks
   - Note platform-specific optimizations

Tone: Professional yet approachable, persuasive but honest. Never misrepresent condition or features. Build buyer trust through transparency.

Output Format:
Return a valid JSON object matching the ListingDraftResult schema exactly. All fields are required."""

WRITER_USER = """Create a compelling marketplace listing based on the following item information:

**Item Details:**
- Item Type: {item_type}
- Brand: {brand}
- Model: {model_name}
- Size: {size}
- Color: {color}
- Condition: {condition}
- Condition Notes: {condition_notes}
- Accessories Included: {accessories_included}
- User Description: {item_description}

**Pricing Context:**
- Suggested Price: £{suggested_price}
- Platform Recommendation: {preferred_platform}

**Price Research Summary:**
{price_research_summary}

**Requirements:**
1. Write an SEO-optimized title (max 80 characters for eBay)
2. Write a compelling description (200-400 words)
3. Suggest 2-3 appropriate categories for {preferred_platform}
4. Recommend a shipping method (UK-focused)
5. Provide returns policy text
6. If preferred_platform is "both", include platform_variants with eBay and Vinted specific tweaks

Generate the complete listing content as structured JSON matching the ListingDraftResult schema."""


class ListingDraftResult(BaseModel):
    """Structured output for listing draft generation.

    Contains all generated content for a marketplace listing,
    including platform-specific variants when listing on multiple platforms.
    """

    title: str = Field(
        ...,
        description="SEO-optimized listing title (max 80 characters for eBay compatibility)",
        max_length=80,
    )
    description: str = Field(
        ...,
        description="Compelling sales copy (200-400 words) covering features, condition, and sizing",
        min_length=100,
        max_length=2000,
    )
    category_suggestions: list[str] = Field(
        ...,
        description="Platform-specific category suggestions in order of relevance",
        min_length=1,
        max_length=5,
    )
    shipping_suggestion: str = Field(
        ...,
        description="Recommended shipping method with UK-focused guidance",
        max_length=500,
    )
    returns_policy: str = Field(
        ...,
        description="Returns policy text compliant with UK consumer rights",
        max_length=500,
    )
    platform_variants: dict[str, dict] = Field(
        default_factory=dict,
        description="Platform-specific overrides when preferred_platform is 'both'. "
        "Keys are platform names ('ebay', 'vinted'), values contain 'title' and/or 'description' tweaks.",
        examples=[
            {
                "ebay": {
                    "title": "Brand Model Item - BNWT Size M",
                    "description": "eBay-specific description variant...",
                },
                "vinted": {
                    "title": "Brand Model Item Size M",
                    "description": "Vinted-specific description variant...",
                },
            }
        ],
    )
