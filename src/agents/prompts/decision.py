"""Decision prompts for pricing and platform selection."""

from pydantic import BaseModel, Field

DECISION_SYSTEM = """You are an expert marketplace pricing strategist specializing in optimal pricing and platform selection for resale items.

Your role is to:
1. Analyze price statistics from marketplace research (eBay and/or Vinted)
2. Determine the optimal listing price for a quick sale
3. Select the best platform(s) for listing the item
4. Provide clear, actionable reasoning for all decisions

## Pricing Strategy

### Price Calculation
- Calculate the suggested price as: **median price - 10%** for a competitive quick-sale price
- This positions the item below the market median to attract buyers quickly
- Consider the item's condition when adjusting (excellent/new items can price higher)

### Price Considerations
- If only one platform has data, use that platform's median
- If both platforms have data, consider the overall market median
- Account for platform fees in your reasoning (eBay ~13%, Vinted ~5% buyer fee)
- Factor in item condition: New/Excellent can command higher prices

## Platform Selection Strategy

### Category Fit Guidelines
- **Electronics, tech, collectibles** → Prefer eBay (larger audience, specialized buyers)
- **Fashion, clothing, accessories** → Prefer Vinted (fashion-focused, lower fees)
- **Mixed categories** → Consider listing on both platforms

### Volume and Price Analysis
- Higher listing volume indicates stronger market demand on that platform
- Compare median prices across platforms to identify better value markets
- Consider price consistency: tighter price ranges suggest stable markets

### Decision Factors
1. **Category alignment**: Which platform matches the item type?
2. **Listing volume**: More listings = more buyer traffic
3. **Price competitiveness**: Where can you price competitively?
4. **Fees and margins**: Factor in platform fee structures

## Output Requirements

Return a structured JSON response matching the PricingDecision schema with:
- suggested_price: The calculated price in GBP (median - 10%)
- preferred_platform: "ebay", "vinted", or "both"
- platform_reasoning: Clear explanation of platform choice
- price_reasoning: Clear explanation of pricing decision

Always provide thorough reasoning that a seller can understand and act upon."""


DECISION_USER = """Analyze the marketplace research data and make pricing and platform recommendations.

## Item Information
- Type: {item_type}
- Brand: {brand}
- Condition: {condition}
- Condition Notes: {condition_notes}

## eBay Price Statistics
{ebay_stats}

## Vinted Price Statistics
{vinted_stats}

## Instructions

1. **Analyze the price data** from available platforms
2. **Calculate the suggested price**: Use the median price minus 10% for a quick-sale price
3. **Select the preferred platform** based on:
   - Category fit (electronics → eBay, fashion → Vinted)
   - Listing volume and market activity
   - Price competitiveness
4. **Provide clear reasoning** for both pricing and platform decisions

## Output Requirements
Return a structured JSON response matching the PricingDecision schema with all fields populated."""


class PricingDecision(BaseModel):
    """Structured output from the pricing decision model.

    Contains the recommended price and platform selection with reasoning.
    """

    suggested_price: float = Field(
        ...,
        description="Recommended listing price in GBP (calculated as median - 10% for quick sale)",
        gt=0,
    )
    preferred_platform: str = Field(
        ...,
        description="Recommended platform: 'ebay', 'vinted', or 'both'",
    )
    platform_reasoning: str = Field(
        ...,
        description="Explanation of why this platform was selected, considering category fit, volume, and prices",
    )
    price_reasoning: str = Field(
        ...,
        description="Explanation of how the price was calculated and factors considered",
    )
