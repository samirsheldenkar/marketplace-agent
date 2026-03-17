# Hybrid eBay/Vinted Listing Agent
## Consolidated Implementation Specification v1.0

**Based on**: technical_specification.md + clarifying decisions  
**Status**: Ready for implementation  
**Date**: 2026-03-17

---

## 1. Executive Summary

A self-hosted Python AI agent that analyzes item photos, researches comparable prices on eBay and Vinted, and generates optimized listing drafts with pricing recommendations.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Vision Model** | Via LiteLLM (model-agnostic) | Allows flexibility (GPT-4o, local vision models, etc.) |
| **Vinted Scraper** | Python library `vinted-scraper` | Cost-effective, acceptable fragility |
| **Currency** | GBP only | MVP scope |
| **Auto-posting** | No | Draft generation only for Phase 1 |
| **User Model** | Single user | Simple API key auth |
| **Image Retention** | Forever | No cleanup needed |
| **Pricing Override** | None | Fixed 10% discount for quick sale |
| **Platform Selection** | Agent decides | No user override in Phase 1 |

---

## 2. Architecture Overview

```
┌─────────────┐     HTTP/Webhook      ┌──────────────────────┐
│     n8n      │ ──────────────────▶   │   Agent Service      │
│  (UI/Flows)  │ ◀──────────────────   │   (FastAPI)          │
└─────────────┘     JSON responses     │                      │
                                        │  ┌────────────────┐  │
                                        │  │  LangGraph     │  │
                                        │  │  Agent Graph   │  │
                                        │  └───┬──────┬─────┘  │
                                        │      │      │        │
                                        │  ┌───▼──┐ ┌─▼─────┐  │
                                        │  │Tools │ │ LLM   │  │
                                        │  │Layer │ │Client │  │
                                        │  └──┬───┘ └──┬────┘  │
                                        └─────┼────────┼───────┘
                                              │        │
                               ┌──────────────┘        └──────────────┐
                               ▼                                      ▼
                     ┌──────────────────┐                  ┌──────────────────┐
                     │  External APIs   │                  │  LiteLLM Gateway │
                     │  - Apify (eBay)  │                  │                  │
                     │  - Vinted Library│                  │  ┌────────────┐  │
                     └──────────────────┘                  │  │  OpenAI    │  │
                                                          │  ├────────────┤  │
                               ┌───────────────┐          │  │  Ollama    │  │
                               │  PostgreSQL   │          │  └────────────┘  │
                               │  + Alembic    │          └──────────────────┘
                               └───────────────┘
                               ┌───────────────┐
                               │  File Storage │
                               │  (images)     │
                               └───────────────┘
```

### Data Flow

1. User uploads images + optional metadata via n8n → `POST /listing`
2. Image analysis (via LiteLLM vision model) identifies item attributes
3. Agent reasoning refines attributes and builds search queries
4. Parallel scraping: eBay (Apify) + Vinted (Python library)
5. Pricing decision: analyze stats, recommend platform, set price
6. Listing writer generates title, description, shipping guidance
7. Quality check validates output
8. Return structured listing draft to n8n

---

## 3. Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11+ |
| Agent Framework | LangGraph | ≥ 0.2 |
| API Framework | FastAPI | ≥ 0.110 |
| LLM Gateway | LiteLLM | Latest |
| Cloud LLM | OpenAI GPT-4o | Latest |
| Local LLM | Ollama (Llama 3) | Latest |
| Database | PostgreSQL | 16+ |
| Migrations | Alembic | Latest |
| Object Storage | Local filesystem | — |
| Workflow / UI | n8n | Latest |
| eBay Scraper | Apify actor | `caffein.dev/ebay-sold-listings` |
| Vinted Scraper | `vinted-scraper` Python library | Latest |
| Logging | structlog | Latest |
| Testing | pytest + pytest-asyncio | Latest |
| Linting | ruff | Latest |
| Type Checking | mypy (strict) | Latest |

---

## 4. Configuration

### Environment Variables (Pydantic Settings)

```python
class Settings(BaseSettings):
    # Database
    database_url: str  # Required
    database_pool_size: int = 10
    database_max_overflow: int = 5

    # LiteLLM
    litellm_url: str = "http://litellm:4000"
    litellm_api_key: str = ""

    # Model routing (all via LiteLLM)
    vision_model: str = "openai/gpt-4o"  # Model-agnostic via LiteLLM
    reasoning_model: str = "openai/gpt-4o"
    drafting_model: str = "ollama/llama3"

    # Agent thresholds
    confidence_threshold: float = 0.7
    price_discount_pct: float = 10.0  # Fixed, not configurable per-request
    max_scraper_results: int = 50
    scraper_timeout_seconds: int = 30

    # Image handling
    max_image_size_mb: int = 10
    max_images_per_listing: int = 10
    allowed_image_formats: list[str] = ["jpeg", "jpg", "png", "webp", "heic"]
    image_storage_path: str = "/data/images"

    # Cost controls
    max_tokens_per_listing: int = 8000
    max_llm_cost_per_listing_usd: float = 0.50

    # Scraper config
    apify_api_token: str = ""  # Required for eBay
    apify_ebay_actor_id: str = "caffein.dev/ebay-sold-listings"
    ebay_country: str = "GB"
    vinted_country: str = "GB"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = ""  # Single-user API key
    api_rate_limit_rpm: int = 30

    class Config:
        env_file = ".env"
        env_prefix = "MARKETPLACE_"
```

### LiteLLM Configuration

```yaml
# litellm_config.yaml
model_list:
  - model_name: vision
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
      max_tokens: 2048

  - model_name: reasoning
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
      max_tokens: 4096

  - model_name: drafting
    litellm_params:
      model: ollama/llama3
      api_base: http://ollama:11434
      max_tokens: 4096

router_settings:
  routing_strategy: "usage-based-routing-v2"
  enable_tag_filtering: true

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

---

## 5. Data Models

### 5.1 Agent State (`ListState`)

```python
from typing import TypedDict, Optional

class PriceStats(TypedDict):
    num_listings: int
    avg_price: float
    median_price: float
    min_price: float
    max_price: float
    items: list[dict]

class ListingDraft(TypedDict):
    title: str                          # ≤ 80 chars
    description: str                    # 200–400 words
    category_suggestions: list[str]
    shipping_suggestion: str
    returns_policy: str

class ListState(TypedDict):
    # Control
    run_id: str
    messages: list
    
    # Item identification
    item_description: str
    item_type: str
    brand: Optional[str]
    model_name: Optional[str]
    size: Optional[str]
    color: Optional[str]
    condition: str                      # "New" | "Excellent" | "Good" | "Fair" | "Poor"
    condition_notes: Optional[str]
    confidence: float
    accessories_included: list[str]
    
    # Images
    photos: list[str]                   # File paths
    image_analysis_raw: Optional[dict]
    
    # Price research
    ebay_price_stats: Optional[PriceStats]
    vinted_price_stats: Optional[PriceStats]
    ebay_query_used: Optional[str]
    vinted_query_used: Optional[str]
    
    # Decision (agent-controlled, no user override)
    suggested_price: Optional[float]    # GBP only
    preferred_platform: Optional[str]   # "ebay" | "vinted" | "both"
    platform_reasoning: Optional[str]
    
    # Output
    listing_draft: Optional[ListingDraft]
    
    # Control flow
    needs_clarification: bool
    clarification_question: Optional[str]
    error_state: Optional[str]
    retry_count: int
```

### 5.2 Database Schema

```sql
-- Table: listings
CREATE TABLE listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'clarification', 'completed', 'failed')),

    -- Item attributes
    item_type VARCHAR(100),
    item_description TEXT,
    brand VARCHAR(100),
    model_name VARCHAR(200),
    size VARCHAR(50),
    color VARCHAR(100),
    condition VARCHAR(20) CHECK (condition IN ('New', 'Excellent', 'Good', 'Fair', 'Poor')),
    condition_notes TEXT,
    confidence REAL,
    accessories_included JSONB DEFAULT '[]',

    -- Pricing (GBP only)
    suggested_price NUMERIC(10,2),
    preferred_platform VARCHAR(10),
    platform_reasoning TEXT,

    -- Generated content
    title VARCHAR(200),
    description TEXT,
    listing_draft JSONB,

    -- Full state snapshot
    raw_state JSONB,

    -- Image paths (retained forever)
    image_paths JSONB DEFAULT '[]'
);

CREATE INDEX idx_listings_status ON listings(status);
CREATE INDEX idx_listings_created_at ON listings(created_at);

-- Table: scrape_runs
CREATE TABLE scrape_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    source VARCHAR(10) NOT NULL CHECK (source IN ('ebay', 'vinted')),
    query_string TEXT NOT NULL,
    stats JSONB,
    raw_items JSONB,
    item_count INTEGER,
    duration_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_scrape_runs_listing_id ON scrape_runs(listing_id);

-- Table: agent_runs (audit log)
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    node_name VARCHAR(50) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'running',
    input_summary JSONB,
    output_summary JSONB,
    error_message TEXT,
    llm_model_used VARCHAR(100),
    token_usage JSONB
);

CREATE INDEX idx_agent_runs_listing_id ON agent_runs(listing_id);
```

---

## 6. Agent Graph Structure

```
START
  ↓
image_analysis (LiteLLM vision model)
  ↓
agent_reasoning (GPT-4o)
  ↓
  ├─ confidence < 0.7 → clarify → (user) → back to agent_reasoning
  ↓
scrape_parallel
  ├─ ebay_scrape (Apify actor)
  └─ vinted_scrape (vinted-scraper library)
  ↓
agent_decision (GPT-4o) → pricing + platform selection
  ↓
listing_writer (Ollama/Llama 3)
  ↓
quality_check (deterministic validation)
  ↓
END
```

### Node Details

| Node | LLM | Purpose | Output |
|------|-----|---------|--------|
| **image_analysis** | LiteLLM vision model | Analyze photos, identify item | Item attributes, confidence |
| **agent_reasoning** | GPT-4o | Refine attributes, build queries | Refined data, search queries |
| **clarify** | GPT-4o | Generate targeted questions | Clarification question |
| **ebay_scrape** | None | Fetch eBay sold listings | PriceStats |
| **vinted_scrape** | None | Fetch Vinted listings | PriceStats |
| **agent_decision** | GPT-4o | Price analysis, platform choice | Price (GBP), platform, reasoning |
| **listing_writer** | Llama 3 | Generate listing copy | Title, description, etc. |
| **quality_check** | None | Validate output constraints | Pass/fail with feedback |

---

## 7. API Contracts

### 7.1 `POST /listing` — Create Listing

**Request**: `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `images` | File[] | Yes (1–10) | Item photos |
| `brand` | string | No | Known brand |
| `size` | string | No | Size info |
| `color` | string | No | Color |
| `notes` | string | No | Free-text context |

**Headers**: `X-API-Key: <api_key>`

**Response (200)**: Completed listing

```json
{
  "listing_id": "uuid",
  "status": "completed",
  "item": {
    "type": "headphones",
    "brand": "Sony",
    "model": "WH-1000XM5",
    "condition": "Good",
    "confidence": 0.91
  },
  "pricing": {
    "suggested_price": 142.00,
    "currency": "GBP",
    "preferred_platform": "ebay",
    "platform_reasoning": "Higher volume and better prices for electronics on eBay",
    "ebay_stats": { "num_listings": 47, "median_price": 158.00 },
    "vinted_stats": { "num_listings": 12, "median_price": 130.00 }
  },
  "listing_draft": {
    "title": "Sony WH-1000XM5 Wireless Headphones - Good Condition",
    "description": "...",
    "category_suggestions": ["Sound & Vision > Headphones"],
    "shipping_suggestion": "Royal Mail 2nd Class Signed For",
    "returns_policy": "30-day returns accepted"
  }
}
```

**Response (202)**: Clarification needed

```json
{
  "listing_id": "uuid",
  "status": "clarification",
  "clarification_question": "Can you confirm the UK shoe size? The images suggest size 9 or 10."
}
```

**Error responses**:
- `400`: Invalid input (no images, wrong format, oversized)
- `401`: Invalid API key
- `429`: Rate limit exceeded
- `500`: Internal error
- `503`: LLM gateway or all scrapers unavailable

### 7.2 `POST /listing/{id}/clarify` — Respond to Clarification

**Request**:
```json
{ "answer": "It's a UK size 10, and includes the original box" }
```

**Headers**: `X-API-Key: <api_key>`

**Response**: Same as `POST /listing` (200 or 202)

### 7.3 `GET /listing/{id}` — Retrieve Listing

**Headers**: `X-API-Key: <api_key>`

**Response**: Same as `POST /listing` 200

### 7.4 `GET /health` — Health Check

**Response**:
```json
{
  "status": "healthy",
  "services": {
    "database": "ok",
    "litellm": "ok",
    "apify": "ok"
  },
  "version": "1.0.0"
}
```

---

## 8. Tools & Scrapers

### 8.1 eBay Scraper (Apify)

```python
async def scrape_ebay_sold_listings(
    query: str,
    country: str = "GB",
    max_results: int = 50
) -> PriceStats:
    """Fetch eBay sold listings via Apify actor."""
```

**Input**: Search query string  
**Output**: PriceStats with sample items  
**Timeout**: 30 seconds  
**Retry**: 2 retries with 2s linear backoff  
**Error handling**: Returns None on failure, continues with Vinted data only

### 8.2 Vinted Scraper (Python Library)

```python
async def scrape_vinted_listings(
    query: str,
    country: str = "GB",
    max_results: int = 50
) -> PriceStats:
    """Fetch Vinted listings via vinted-scraper library."""
```

**Input**: Search query string  
**Output**: PriceStats with sample items  
**Timeout**: 30 seconds  
**Retry**: 2 retries with 2s linear backoff  
**Error handling**: Returns None on failure, continues with eBay data only  
**Note**: Library wrapped with `asyncio.to_thread()` for async compatibility

---

## 9. Error Handling & Resilience

### 9.1 Retry Policies

| Component | Max Retries | Backoff |
|-----------|-------------|---------|
| LLM calls | 3 | Exponential (1s, 2s, 4s) |
| eBay scraper | 2 | Linear (2s) |
| Vinted scraper | 2 | Linear (2s) |
| Database writes | 3 | Exponential (0.5s, 1s, 2s) |

### 9.2 Circuit Breaker

- Open after 5 failures in 60s
- Cooldown: 30s
- Test request to close

### 9.3 Graceful Degradation

| Failure | Agent Behaviour |
|---------|-----------------|
| eBay scraper fails | Use Vinted only; add caveat |
| Vinted scraper fails | Use eBay only; add caveat |
| Both scrapers fail | Skip pricing; generate listing with user info; flag for manual pricing |
| Vision LLM fails | Set confidence to 0; route to clarification |
| Drafting LLM fails | Fall back to reasoning LLM |
| Reasoning LLM fails | Return error; cannot proceed |

---

## 10. Security

### 10.1 Authentication

- Single API key via `X-API-Key` header
- Configured via `MARKETPLACE_API_KEY` env var

### 10.2 Privacy

- EXIF metadata stripped from images before storage
- PII never logged
- Ollama preferred for verbose content
- Images stored locally only

### 10.3 Rate Limiting

- 30 requests per minute per API key
- Vinted requests throttled to 1 req/s

---

## 11. Observability

### 11.1 Structured Logging (structlog)

```python
logger.info("scrape_completed",
    source="ebay",
    listing_id=listing_id,
    num_results=47,
    duration_ms=2340,
)
```

### 11.2 Metrics (Prometheus)

- `listing_duration_seconds` (histogram)
- `scraper_duration_seconds` (histogram)
- `scraper_error_total` (counter)
- `llm_tokens_total` (counter)
- `llm_cost_usd_total` (counter)

---

## 12. Project Structure

```
marketplace-agent/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── schemas.py
│   │   ├── dependencies.py
│   │   └── middleware.py        # API key auth, rate limiting
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── image_analysis.py      # LiteLLM vision
│   │   │   ├── agent_reasoning.py
│   │   │   ├── clarify.py
│   │   │   ├── scrape_ebay.py         # Apify
│   │   │   ├── scrape_vinted.py       # vinted-scraper
│   │   │   ├── agent_decision.py
│   │   │   ├── listing_writer.py
│   │   │   └── quality_check.py
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── image_analysis.py
│   │       ├── reasoning.py
│   │       ├── clarification.py
│   │       ├── decision.py
│   │       └── listing_writer.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── ebay_scraper.py
│   │   └── vinted_scraper.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   └── database.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── image_service.py
│   │   └── pricing_service.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   └── repositories.py
│   ├── exceptions.py
│   ├── config.py
│   └── main.py
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── fixtures/
│   └── conftest.py
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── litellm_config.yaml
├── n8n/
│   └── workflows/
│       └── listing_workflow.json
├── pyproject.toml
├── .env.example
├── README.md
└── AGENTS.md
```

---

## 13. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Project scaffolding, Docker Compose, CI
- [ ] Database schema + Alembic migrations
- [ ] Configuration management
- [ ] LiteLLM gateway setup
- [ ] Health check endpoint
- [ ] Image upload + validation pipeline

### Phase 2: Core Agent (Week 2)
- [ ] Image analysis node (LiteLLM vision)
- [ ] Agent reasoning node
- [ ] Clarification flow (pause/resume)
- [ ] eBay scraper tool (Apify)
- [ ] Vinted scraper tool (vinted-scraper)
- [ ] LangGraph graph assembly

### Phase 3: Intelligence (Week 3)
- [ ] Pricing decision node
- [ ] Listing writer node
- [ ] Quality check node
- [ ] Full API endpoints
- [ ] Error handling + graceful degradation

### Phase 4: Production (Week 4)
- [ ] n8n workflow template
- [ ] Structured logging + metrics
- [ ] Rate limiting + API key auth
- [ ] Comprehensive test suite
- [ ] Documentation

---

## 14. Success Criteria

- [ ] Happy path: Images → listing draft in < 60s
- [ ] Clarification flow works end-to-end
- [ ] Graceful degradation when scrapers fail
- [ ] All LLM outputs structured (no free-text parsing)
- [ ] > 80% unit test coverage
- [ ] API contract fully implemented
- [ ] n8n workflow functional

---

*End of Consolidated Specification*
