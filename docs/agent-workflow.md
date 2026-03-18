# Agent Workflow

This document explains how the AI agent processes item photos to generate marketplace listings, detailing each step of the workflow.

## Overview

The Marketplace Listing Agent uses a **state machine architecture** powered by LangGraph. Each listing flows through a series of nodes that transform the input (photos) into output (listing drafts).

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INPUT PHASE                                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  User uploads 1-10 images + optional metadata (brand, size)  │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
└─────────────────────────────┼──────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      NODE 1: IMAGE ANALYSIS                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Model: GPT-4o Vision                                        │  │
│  │                                                              │  │
│  │  Input: Image file paths                                     │  │
│  │  Process:                                                    │  │
│  │    1. Load images from disk                                  │  │
│  │    2. Encode as base64                                       │  │
│  │    3. Send to vision model                                   │  │
│  │    4. Extract structured attributes                          │  │
│  │                                                              │  │
│  │  Output:                                                     │  │
│  │    • item_type (e.g., "headphones", "jacket")               │  │
│  │    • brand (e.g., "Sony", "Nike")                           │  │
│  │    • model_name (e.g., "WH-1000XM5")                        │  │
│  │    • size (e.g., "Large", "US 10")                          │  │
│  │    • color (e.g., "Black", "Navy Blue")                     │  │
│  │    • condition (New/Excellent/Good/Fair/Poor)               │  │
│  │    • confidence (0.0 - 1.0)                                 │  │
│  │    • accessories_included [...]                             │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
└─────────────────────────────┼──────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     NODE 2: AGENT REASONING                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Model: GPT-4o Reasoning                                     │  │
│  │                                                              │  │
│  │  Input: Image analysis results + user metadata               │  │
│  │  Process:                                                    │  │
│  │    1. Merge vision results with user hints                   │  │
│  │    2. Normalize item attributes                              │  │
│  │    3. Build optimized search queries                         │  │
│  │    4. Calculate confidence score                             │  │
│  │                                                              │  │
│  │  Output:                                                     │  │
│  │    • Normalized item attributes                              │  │
│  │    • ebay_query_used (optimized search)                     │  │
│  │    • vinted_query_used (optimized search)                   │  │
│  │    • confidence score                                        │  │
│  │    • needs_clarification (true/false)                       │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
└─────────────────────────────┼──────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
           ┌────────▼────────┐  ┌───────▼────────┐
           │ confidence < 0.7│  │confidence ≥ 0.7│
           │                 │  │                │
           └────────┬────────┘  └───────┬────────┘
                    │                   │
                    ▼                   ▼
┌─────────────────────────┐  ┌──────────────────────────────────────┐
│   CLARIFICATION LOOP    │  │     NODE 3: PARALLEL SCRAPING        │
│                         │  │                                      │
│  Generate question for  │  │  ┌────────────────────────────────┐ │
│  user (e.g., "What size │  │  │ scrape_ebay (Apify)            │ │
│   is this jacket?")     │  │  │  • Search eBay sold listings  │ │
│                         │  │  │  • Get 20-50 comparable items │ │
│  ←─── User answers ─────│  │  │  • Extract prices             │ │
│                         │  │  └────────────────┬───────────────┘ │
│  Return to reasoning    │  │                   │                │
│  (loop until confident) │  │  ┌────────────────┴──────────────┐ │
└─────────────────────────┘  │  │ scrape_vinted (Apify)         │ │
                             │  │  • Search Vinted listings     │ │
                             │  │  • Get comparable items       │ │
                             │  │  • Extract prices             │ │
                             │  └────────────────┬───────────────┘ │
                             └───────────────────┼─────────────────┘
                                                 │
                                                 ▼ (fan-in)
┌─────────────────────────────────────────────────────────────────────┐
│                     NODE 4: AGENT DECISION                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Purpose: Calculate pricing and choose platform              │  │
│  │                                                              │  │
│  │  Input: eBay and Vinted price statistics                     │  │
│  │  Process:                                                    │  │
│  │    1. Calculate median prices from both platforms            │  │
│  │    2. Apply fast_sale discount if requested                  │  │
│  │    3. Compare listing volumes                                │  │
│  │    4. Determine best platform                                │  │
│  │                                                              │  │
│  │  Logic:                                                      │  │
│  │    suggested_price = median(all_prices)                     │  │
│  │    if fast_sale:                                            │  │
│  │      suggested_price *= (1 - discount_pct/100)              │  │
│  │                                                              │  │
│  │    if ebay_volume > 2 * vinted_volume:                      │  │
│  │      preferred_platform = "ebay"                            │  │
│  │    elif vinted_volume > 2 * ebay_volume:                    │  │
│  │      preferred_platform = "vinted"                          │  │
│  │    else:                                                    │  │
│  │      preferred_platform = "both"                            │  │
│  │                                                              │  │
│  │  Output:                                                     │  │
│  │    • suggested_price (GBP)                                  │  │
│  │    • preferred_platform                                     │  │
│  │    • platform_reasoning                                     │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
└─────────────────────────────┼──────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    NODE 5: LISTING WRITER                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Model: Llama 3 (Ollama) with GPT-4o fallback                │  │
│  │                                                              │  │
│  │  Input: All item attributes + pricing + platform decision    │  │
│  │  Process:                                                    │  │
│  │    1. Analyze market research data                           │  │
│  │    2. Generate SEO-optimized title                           │  │
│  │    3. Write detailed description                             │  │
│  │    4. Suggest categories                                     │  │
│  │    5. Recommend shipping method                              │  │
│  │    6. Draft returns policy                                   │  │
│  │    7. Create platform-specific variants                      │  │
│  │                                                              │  │
│  │  Output (ListingDraft):                                      │  │
│  │    • title (80 chars optimized)                             │  │
│  │    • description (HTML/markdown)                            │  │
│  │    • category_suggestions [...]                             │  │
│  │    • shipping_suggestion                                    │  │
│  │    • returns_policy                                         │  │
│  │    • platform_variants {ebay: {...}, vinted: {...}}        │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
└─────────────────────────────┼──────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    NODE 6: QUALITY CHECK                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Purpose: Validate listing quality                           │  │
│  │                                                              │  │
│  │  Checks:                                                     │  │
│  │    ✓ Title length (30-80 characters)                        │  │
│  │    ✓ Title quality (keywords, capitalization)               │  │
│  │    ✓ Description length (>200 characters)                   │  │
│  │    ✓ Price reasonableness (within market range)             │  │
│  │    ✓ Category suggestions present                           │  │
│  │                                                              │  │
│  │  Output:                                                     │  │
│  │    • quality_passed (true/false)                            │  │
│  │    • quality_issues [...] (if any)                         │  │
│  │    • retry_count                                            │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
└─────────────────────────────┼──────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
          ┌─────────▼────────┐ ┌────────▼────────┐
          │ quality_passed   │ │ quality_failed  │
          │                  │ │ & retry < 2     │
          └─────────┬────────┘ └────────┬────────┘
                    │                   │
                    │                   └──────┐
                    │                          │
                    ▼                          ▼
┌─────────────────────────┐      ┌──────────────────────────────┐
│      END (Success)      │      │ Return to listing_writer     │
│                         │      │ (retry with feedback)        │
│  Return listing draft   │      └──────────────────────────────┘
│  with all data          │
└─────────────────────────┘
```

## State Management

The agent maintains state throughout the workflow using the `ListState` TypedDict:

```python
class ListState(TypedDict):
    # Control
    run_id: str                    # Unique listing ID
    messages: list[Any]            # Conversation history
    
    # Item identification
    item_type: str                 # Category (e.g., "headphones")
    brand: str | None              # Brand name
    model_name: str | None         # Model identifier
    size: str | None               # Size if applicable
    color: str | None              # Primary color
    condition: str                 # Condition grade
    condition_notes: str | None    # Additional condition info
    confidence: float              # 0.0 - 1.0
    accessories_included: list[str]
    
    # Images
    photos: list[str]              # File paths
    image_analysis_raw: dict | None
    
    # Price research
    ebay_price_stats: PriceStats | None
    vinted_price_stats: PriceStats | None
    ebay_query_used: str | None
    vinted_query_used: str | None
    
    # Decision
    suggested_price: float | None
    preferred_platform: str | None  # "ebay" | "vinted" | "both"
    platform_reasoning: str | None
    fast_sale: bool                # User preference
    
    # Output
    listing_draft: NotRequired[ListingDraft | None]
    
    # Control flow
    needs_clarification: bool
    clarification_question: NotRequired[str | None]
    ebay_error: NotRequired[str | None]
    vinted_error: NotRequired[str | None]
    quality_retry_count: Annotated[int, operator.add]
    clarification_count: Annotated[int, operator.add]
```

## Example Workflow Walkthrough

### Scenario: Selling a Used Headphone

**Step 1: User Input**
- Uploads 3 images of Sony WH-1000XM5 headphones
- Notes: "Light scratches on ear cups, works perfectly"
- Fast sale: Yes

**Step 2: Image Analysis**
```json
{
  "item_type": "headphones",
  "brand": "Sony",
  "model_name": "WH-1000XM5",
  "color": "Black",
  "condition": "Good",
  "accessories_included": ["carrying case", "cable"],
  "confidence": 0.92
}
```

**Step 3: Agent Reasoning**
- Merges image analysis with user condition notes
- Generates search queries:
  - eBay: `Sony WH-1000XM5 used headphones`
  - Vinted: `Sony WH-1000XM5`
- Confidence: 0.92 (above 0.7 threshold) → proceed to scraping

**Step 4: Parallel Scraping**
- eBay results: 45 sold listings, median £220, avg £235
- Vinted results: 12 listings, median £200, avg £210

**Step 5: Agent Decision**
- Calculate suggested price:
  - Median of both: (£220 + £200) / 2 = £210
  - Fast sale discount 10%: £210 × 0.9 = £189
- Determine platform:
  - eBay has 45 vs Vinted 12 (3.75x more)
  - Preferred platform: "ebay"

**Step 6: Listing Writer**
Generates:
```json
{
  "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones - Black",
  "description": "Selling my excellent Sony WH-1000XM5 headphones...",
  "category_suggestions": ["Consumer Electronics", "Headphones"],
  "shipping_suggestion": "Royal Mail Tracked 48",
  "returns_policy": "30-day returns accepted",
  "platform_variants": {
    "ebay": {"title": "Sony WH-1000XM5...", "description": "..."},
    "vinted": {"title": "Sony Headphones WH-1000XM5", "description": "..."}
  }
}
```

**Step 7: Quality Check**
- ✓ Title: 62 characters (good)
- ✓ Description: 450 characters (good)
- ✓ Price: £189 within market range (£200-£235)
- ✓ Categories present
- **Result**: PASSED

**Final Output**
Listing is saved with status "COMPLETED" and returned to user.

## Clarification Scenarios

### Low Confidence Example

**Image Analysis Output**:
```json
{
  "item_type": "electronics",
  "brand": "Unknown",
  "model_name": null,
  "confidence": 0.45
}
```

**Agent Decision**: confidence (0.45) < threshold (0.7) → needs clarification

**Clarification Question Generated**:
> "I can see this is an electronic device, but I'm having trouble identifying the specific item. Could you tell me: 1) What type of item is this (e.g., headphones, speaker, camera)? 2) What brand is it, if visible? 3) Are there any model numbers or identifying marks?"

**User Response**:
> "It's Bose SoundLink Mini II speaker"

**Return to Reasoning**:
- Merge clarification into state
- Re-analyze with new information
- Confidence increases to 0.88
- Proceed with scraping

## Error Handling

### Graceful Degradation

The agent handles failures at each node:

| Node | Failure Mode | Fallback Behavior |
|------|--------------|-------------------|
| Image Analysis | Vision model unavailable | Return "unknown" with 0 confidence → trigger clarification |
| Scraping | eBay scraper fails | Use only Vinted data, or estimate price |
| Scraping | Both scrapers fail | Use generic pricing based on item category |
| Listing Writer | Ollama unavailable | Fall back to GPT-4o for drafting |
| Quality Check | Persistent failures | Return best attempt with warnings |

### Retry Logic

- **Agent Reasoning**: 3 retries with exponential backoff (1s, 2s, 4s)
- **Listing Writer**: 3 retries, then fallback model
- **Quality Check**: 2 retries before accepting

## Performance Characteristics

### Typical Timing

| Node | Average Duration | Notes |
|------|------------------|-------|
| Image Analysis | 3-5 seconds | Depends on image count |
| Agent Reasoning | 2-3 seconds | Single LLM call |
| Scraping (parallel) | 10-15 seconds | Depends on Apify queue |
| Agent Decision | <100ms | Local calculation |
| Listing Writer | 5-8 seconds | Local Ollama is fast |
| Quality Check | 1-2 seconds | Validation logic |
| **Total** | **25-35 seconds** | End-to-end |

### Optimization Tips

1. **Image Count**: Use 3-5 images for best speed/accuracy balance
2. **Image Size**: Pre-resize images to <2MB for faster upload
3. **Apify Performance**: Paid Apify plans have faster scraping
4. **Ollama**: Run on GPU for faster drafting

## Customization

### Modifying Confidence Threshold

```python
# In .env
MARKETPLACE_CONFIDENCE_THRESHOLD=0.6  # More lenient
MARKETPLACE_CONFIDENCE_THRESHOLD=0.8  # More strict
```

### Adjusting Price Calculation

```python
# In src/services/pricing_service.py
def calculate_suggested_price(self, ebay_stats, vinted_stats, fast_sale=True):
    # Custom logic here
    # Example: Weight eBay more heavily
    if ebay_stats and vinted_stats:
        weighted_avg = (ebay_stats['median'] * 0.6 + 
                       vinted_stats['median'] * 0.4)
        return weighted_avg
```

### Adding Custom Quality Checks

```python
# In src/agents/nodes/quality_check.py
def quality_check(state: ListState) -> dict:
    issues = []
    
    # Add custom check
    if state.get('item_type') == 'electronics':
        draft = state.get('listing_draft', {})
        if 'warranty' not in draft.get('description', '').lower():
            issues.append("Electronics listings should mention warranty status")
    
    # ... rest of checks
```
