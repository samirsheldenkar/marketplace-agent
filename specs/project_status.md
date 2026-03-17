# Project Status: Hybrid eBay/Vinted Listing Agent

**Last Updated**: 2026-03-17  
**Current Phase**: Phase 1 Complete (Foundation)  
**Next Phase**: Phase 2 (Core Agent)

---

## Summary

The marketplace listing agent project foundation has been established with a complete project structure, Docker infrastructure, database schema, and core service scaffolding. The system is ready for LangGraph agent implementation.

---

## Completed (Phase 1: Foundation)

### Project Structure (53 files created)
- [x] Full directory structure with proper Python package layout
- [x] Source code organization (api/, agents/, tools/, models/, services/, db/)
- [x] Test structure (unit/, integration/, e2e/, fixtures/)
- [x] Docker infrastructure
- [x] Alembic migration setup
- [x] Configuration management

### Configuration & Dependencies
- [x] `pyproject.toml` with complete dependency list:
  - FastAPI, LangGraph, LangChain, LiteLLM
  - SQLAlchemy (async), Alembic, PostgreSQL
  - Testing: pytest, pytest-asyncio, pytest-cov
  - Linting: ruff, mypy
  - Utilities: structlog, Pillow, httpx
- [x] Pydantic Settings (`src/config.py`) with all environment variables
- [x] `.env.example` template

### Docker Infrastructure
- [x] Multi-stage `Dockerfile` (builder + production stages)
- [x] `docker-compose.yml` with all services:
  - PostgreSQL 16
  - Ollama (local LLMs)
  - LiteLLM gateway
  - Agent service
  - n8n
- [x] `litellm_config.yaml` with model routing:
  - vision: openai/gpt-4o
  - reasoning: openai/gpt-4o
  - drafting: ollama/llama3
- [x] Health checks for all services

### Database Layer
- [x] SQLAlchemy models (`src/models/database.py`):
  - `Listing` - main entity with item attributes, pricing, draft content
  - `ScrapeRun` - audit trail for marketplace queries
  - `AgentRun` - node execution audit log
- [x] TypedDict state definition (`src/models/state.py`):
  - `ListState` - complete LangGraph state
  - `PriceStats` - price statistics structure
  - `ListingDraft` - generated content structure
- [x] Alembic configuration:
  - `alembic.ini` - migration config
  - `env.py` - async migration environment
  - `versions/001_initial_schema.py` - initial schema migration
- [x] Async database session management (`src/db/session.py`)

### API Layer (Foundation)
- [x] FastAPI app (`src/main.py`) with:
  - Lifespan management
  - CORS middleware
  - Health check endpoint
- [x] API schemas (`src/api/schemas.py`):
  - Request/response models
  - PriceStats, ListingDraft, ItemInfo, PricingInfo
  - CreateListingRequest/Response
  - ClarificationRequest/Response
  - GetListingResponse, HealthResponse
- [x] API dependencies (`src/api/dependencies.py`):
  - API key authentication
  - `verify_api_key()` dependency
- [x] Middleware (`src/api/middleware.py`):
  - CORS configuration
  - GZip compression
  - Request timing middleware
- [x] Route definitions (`src/api/routes.py`) - skeleton endpoints:
  - `POST /listing` - create listing
  - `POST /listing/{id}/clarify` - submit clarification
  - `GET /listing/{id}` - retrieve listing

### Services
- [x] Image service (`src/services/image_service.py`):
  - Image validation (format, size)
  - Image storage with UUID filenames
  - Directory organization by listing_id
- [x] Pricing service (`src/services/pricing_service.py`):
  - Suggested price calculation (median - 10%)
  - Platform preference determination (eBay vs Vinted vs both)

### Error Handling
- [x] Exception hierarchy (`src/exceptions.py`):
  - `MarketplaceAgentError` (base)
  - `ScraperError`
  - `LLMError`
  - `ValidationError`
  - `ImageProcessingError`
  - `ClarificationTimeoutError`

### Documentation
- [x] `README.md` with quick start guide
- [x] `specs/consolidated_spec.md` - full implementation specification
- [x] `AGENTS.md` - development guidelines (from repo)

---

## Remaining Work

### Phase 2: Core Agent (Week 2)

#### Tools Layer
- [ ] eBay scraper (`src/tools/ebay_scraper.py`)
  - Apify actor integration
  - Async client with retry logic
  - Response normalization to PriceStats
  - Timeout and error handling
  
- [ ] Vinted scraper (`src/tools/vinted_scraper.py`)
  - `vinted-scraper` library integration
  - `asyncio.to_thread()` wrapper for sync library
  - Response normalization to PriceStats
  - Rate limiting (1 req/s)

#### LangGraph Nodes
- [ ] Image analysis node (`src/agents/nodes/image_analysis.py`)
  - LiteLLM vision model integration
  - Multimodal prompt for image understanding
  - Structured output parsing (item_type, brand, model, condition, confidence)
  - Confidence threshold check
  
- [ ] Agent reasoning node (`src/agents/nodes/agent_reasoning.py`)
  - Merge image analysis with user metadata
  - Construct optimized search queries for eBay/Vinted
  - Evaluate confidence against threshold
  - Route to clarification or scraping
  
- [ ] Clarification node (`src/agents/nodes/clarify.py`)
  - Generate targeted questions (max 2)
  - Track clarification round count
  - Halt graph execution for user input
  - Resume capability
  
- [ ] eBay scrape node (`src/agents/nodes/scrape_ebay.py`)
  - Tool node integration
  - Parallel execution support
  - Error handling and stats storage
  
- [ ] Vinted scrape node (`src/agents/nodes/scrape_vinted.py`)
  - Tool node integration
  - Parallel execution support
  - Error handling and stats storage

#### Agent Graph
- [ ] Graph assembly (`src/agents/graph.py`)
  - StateGraph definition
  - Node registration
  - Edge routing logic
  - Parallel scraping fan-out/fan-in
  - Clarification loop
  - Checkpoint persistence (SqliteSaver/PostgresSaver)

#### Prompts
- [ ] Image analysis prompts (`src/agents/prompts/image_analysis.py`)
- [ ] Reasoning prompts (`src/agents/prompts/reasoning.py`)
- [ ] Clarification prompts (`src/agents/prompts/clarification.py`)

#### Database Repositories
- [ ] Repository pattern (`src/db/repositories.py`)
  - ListingRepository
  - ScrapeRunRepository
  - AgentRunRepository

---

### Phase 3: Intelligence (Week 3)

#### LangGraph Nodes (Continued)
- [ ] Agent decision node (`src/agents/nodes/agent_decision.py`)
  - Price analysis using PricingService
  - Platform selection logic
  - Structured output: suggested_price, preferred_platform, platform_reasoning
  
- [ ] Listing writer node (`src/agents/nodes/listing_writer.py`)
  - Ollama/Llama 3 integration via LiteLLM
  - Title generation (≤ 80 chars)
  - Description generation (200-400 words)
  - Category suggestions
  - Shipping and returns guidance
  
- [ ] Quality check node (`src/agents/nodes/quality_check.py`)
  - Title length validation
  - Description word count validation
  - Price reasonableness check
  - Placeholder text detection
  - Retry logic with feedback

#### API Implementation
- [ ] Complete route implementations (`src/api/routes.py`)
  - Image upload handling
  - LangGraph execution
  - Clarification state management
  - Error responses
  - Response serialization

#### Prompts (Continued)
- [ ] Decision prompts (`src/agents/prompts/decision.py`)
- [ ] Listing writer prompts (`src/agents/prompts/listing_writer.py`)

---

### Phase 4: Production Readiness (Week 4)

#### Observability
- [ ] Structured logging (`structlog`)
  - JSON output format
  - Context injection
  - Log levels (DEBUG, INFO, WARNING, ERROR)
  - PII redaction
  
- [ ] Prometheus metrics endpoint
  - `listing_duration_seconds` histogram
  - `scraper_duration_seconds` histogram
  - `scraper_error_total` counter
  - `llm_tokens_total` counter
  - `llm_cost_usd_total` counter
  - `listings_total` counter

#### Security & Rate Limiting
- [ ] Rate limiting middleware
  - 30 RPM per API key
  - Vinted scraper throttling (1 req/s)
  
- [ ] Input sanitization
  - Image EXIF stripping
  - Free-text input limits (2000 chars)
  - SQL injection prevention (parameterized queries)

#### n8n Integration
- [ ] Workflow template (`n8n/workflows/listing_workflow.json`)
  - Trigger node
  - HTTP request to agent service
  - Clarification loop
  - Result display
  - Error handling

#### Testing
- [ ] Unit tests (`tests/unit/`)
  - Image service tests
  - Pricing service tests
  - Node logic tests
  - Exception handling tests
  
- [ ] Integration tests (`tests/integration/`)
  - API endpoint tests
  - Database operation tests
  - Scraper tests (mocked)
  
- [ ] E2E tests (`tests/e2e/`)
  - Happy path workflow
  - Clarification flow
  - Degradation scenarios
  
- [ ] Test fixtures (`tests/fixtures/`)
  - Sample images
  - Mock LLM responses
  - Mock scraper responses

#### Documentation
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Deployment guide
- [ ] Troubleshooting guide
- [ ] n8n workflow setup guide

#### CI/CD
- [ ] GitHub Actions workflow
  - Linting (ruff)
  - Type checking (mypy)
  - Testing (pytest)
  - Docker build
  - Security scanning

---

## Implementation Notes

### Key Decisions Finalized
1. **Vision Model**: Via LiteLLM (model-agnostic, default GPT-4o)
2. **Vinted Scraper**: Python `vinted-scraper` library (not Apify)
3. **Currency**: GBP only
4. **Auto-posting**: Not in Phase 1 (drafts only)
5. **User Model**: Single user with API key
6. **Image Retention**: Forever
7. **Pricing**: Fixed 10% discount from median
8. **Platform Selection**: Agent decides (no user override)

### Technical Debt / Known Issues
- [ ] LSP import errors (dependencies not installed in dev environment)
- [ ] Route implementations are skeletons (return 501 Not Implemented)
- [ ] No circuit breaker implementation yet
- [ ] No retry logic implemented yet
- [ ] Test files are empty

### Resolved Issues
- [x] Database initialization creates tables but doesn't run migrations yet (Resolved - Alembic initialized and migrations generated)
- [x] Image sizes not using megabytes specification
- [x] LiteLLM models incorrectly defaulted in config
- [x] Missing `fast_sale` parameter on API
- [x] Missing `platform_variants` in `ListingDraft` state
- [x] Incorrect DB types (`Float` to `Numeric(10,2)`) and missing `CHECK` constraint on status
- [x] Pricing skew in `PricingService` logic

### Blockers
None. Ready to proceed with Phase 2.

---

## File Inventory

### Source Code (30 files)
```
src/
├── __init__.py
├── main.py
├── config.py
├── exceptions.py
├── api/
│   ├── __init__.py
│   ├── routes.py
│   ├── schemas.py
│   ├── dependencies.py
│   └── middleware.py
├── agents/
│   ├── __init__.py
│   ├── graph.py (skeleton)
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── image_analysis.py (skeleton)
│   │   ├── agent_reasoning.py (skeleton)
│   │   ├── clarify.py (skeleton)
│   │   ├── scrape_ebay.py (skeleton)
│   │   ├── scrape_vinted.py (skeleton)
│   │   ├── agent_decision.py (skeleton)
│   │   ├── listing_writer.py (skeleton)
│   │   └── quality_check.py (skeleton)
│   └── prompts/
│       ├── __init__.py
│       ├── image_analysis.py (skeleton)
│       ├── reasoning.py (skeleton)
│       ├── clarification.py (skeleton)
│       ├── decision.py (skeleton)
│       └── listing_writer.py (skeleton)
├── tools/
│   ├── __init__.py
│   ├── ebay_scraper.py (skeleton)
│   └── vinted_scraper.py (skeleton)
├── models/
│   ├── __init__.py
│   ├── state.py
│   └── database.py
├── services/
│   ├── __init__.py
│   ├── image_service.py
│   └── pricing_service.py
└── db/
    ├── __init__.py
    ├── session.py
    └── repositories.py (skeleton)
```

### Configuration & Infrastructure (9 files)
```
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── litellm_config.yaml
├── alembic/
│   ├── alembic.ini
│   ├── script.py.mako
│   ├── env.py
│   └── versions/
│       ├── __init__.py
│       └── 84cd96a0000f_update_schema_types_and_constraints.py
├── pyproject.toml
└── .env.example
```

### Tests (7 files)
```
tests/
├── __init__.py
├── conftest.py (skeleton)
├── unit/
│   └── __init__.py
├── integration/
│   └── __init__.py
├── e2e/
│   └── __init__.py
└── fixtures/
    └── __init__.py
```

### Documentation (4 files)
```
├── specs/
│   ├── initial_spec.md
│   ├── technical_specification.md
│   ├── consolidated_spec.md
│   └── project_status.md (this file)
├── README.md
└── AGENTS.md
```

### n8n (1 file)
```
n8n/
└── workflows/
    └── __init__.py (skeleton)
```

**Total**: 50 files

---

## Next Immediate Actions

To begin Phase 2, implement in this order:

1. **Scraper Tools** (parallel work possible):
   - `src/tools/ebay_scraper.py` - Apify integration
   - `src/tools/vinted_scraper.py` - vinted-scraper library wrapper

2. **Image Analysis Node**:
   - `src/agents/prompts/image_analysis.py` - Vision prompts
   - `src/agents/nodes/image_analysis.py` - Node implementation

3. **Agent Reasoning Node**:
   - `src/agents/prompts/reasoning.py` - Reasoning prompts
   - `src/agents/nodes/agent_reasoning.py` - Node implementation

4. **Clarification Node**:
   - `src/agents/prompts/clarification.py` - Clarification prompts
   - `src/agents/nodes/clarify.py` - Node implementation

5. **Graph Assembly**:
   - `src/agents/graph.py` - Complete graph wiring
   - Test the flow end-to-end

---

*End of Project Status Document*
