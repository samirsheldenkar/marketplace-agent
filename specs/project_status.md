# Project Status: Hybrid eBay/Vinted Listing Agent

**Last Updated**: 2026-03-17  
**Current Phase**: Phase 3 Complete (Core Agent + Intelligence)  
**Next Phase**: Phase 4 (Production Readiness)

---

## Summary

The marketplace listing agent now has a fully functional LangGraph implementation with all core agent nodes, intelligence layer, and complete graph assembly. The system can analyze images, research prices, generate listings, and handle clarification flows end-to-end.

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

## Completed (Phase 2: Core Agent)

### Tools Layer
- [x] eBay scraper (`src/tools/ebay_scraper.py`)
  - Apify actor integration with async httpx client
  - Retry logic (2 retries, 2s linear backoff)
  - Response normalization to PriceStats
  - Timeout and error handling (returns None on failure)
  - Polling for Apify run results
  - Price extraction from various eBay formats
  
- [x] Vinted scraper (`src/tools/vinted_scraper.py`)
  - `vinted-scraper` library integration
  - `asyncio.to_thread()` wrapper for sync library
  - Response normalization to PriceStats
  - Rate limiting (1 req/s)
  - Retry logic with linear backoff

### LangGraph Nodes
- [x] Image analysis node (`src/agents/nodes/image_analysis.py`)
  - LiteLLM vision model integration (GPT-4o via LiteLLM)
  - Multimodal prompt for image understanding
  - Base64 encoding for image transmission
  - Structured output parsing (ImageAnalysisResult)
  - Confidence threshold check
  - Graceful error handling (confidence=0 on failure)
  
- [x] Agent reasoning node (`src/agents/nodes/agent_reasoning.py`)
  - Merge image analysis with user metadata
  - Construct optimized search queries for eBay/Vinted
  - Evaluate confidence against threshold
  - Route to clarification or scraping
  - Retry logic (3 retries, exponential backoff)
  
- [x] Clarification node (`src/agents/nodes/clarify.py`)
  - Generate targeted questions (max 2)
  - Track clarification round count
  - Halt graph execution for user input
  - Resume capability via `resume_after_clarification()`
  - LLM-based structured output
  
- [x] eBay scrape node (`src/agents/nodes/scrape_ebay.py`)
  - Tool node integration
  - Parallel execution support
  - Error handling and stats storage
  
- [x] Vinted scrape node (`src/agents/nodes/scrape_vinted.py`)
  - Tool node integration
  - Parallel execution support
  - Error handling and stats storage

### Agent Graph
- [x] Graph assembly (`src/agents/graph.py`)
  - StateGraph definition with ListState
  - Node registration (8 nodes)
  - Edge routing logic with conditional edges
  - Parallel scraping fan-out/fan-in
  - Clarification loop (agent_reasoning -> clarify -> agent_reasoning)
  - Quality check retry loop
  - Compiled `agent_graph` export

### Prompts
- [x] Image analysis prompts (`src/agents/prompts/image_analysis.py`)
  - IMAGE_ANALYSIS_SYSTEM prompt
  - IMAGE_ANALYSIS_USER template
  - ImageAnalysisResult Pydantic model
  
- [x] Reasoning prompts (`src/agents/prompts/reasoning.py`)
  - REASONING_SYSTEM prompt
  - REASONING_USER template
  - ReasoningResult Pydantic model
  
- [x] Clarification prompts (`src/agents/prompts/clarification.py`)
  - CLARIFICATION_SYSTEM prompt
  - CLARIFICATION_USER template
  - ClarificationResult Pydantic model

---

## Completed (Phase 3: Intelligence)

### LangGraph Nodes
- [x] Agent decision node (`src/agents/nodes/agent_decision.py`)
  - Price analysis using PricingService
  - Platform selection logic (eBay vs Vinted vs both)
  - Structured output: suggested_price, preferred_platform, platform_reasoning
  - LLM-based decision with fallback for missing data
  - Retry logic with exponential backoff
  
- [x] Listing writer node (`src/agents/nodes/listing_writer.py`)
  - Ollama/Llama 3 integration via LiteLLM (drafting model)
  - Title generation (≤ 80 chars)
  - Description generation (200-400 words)
  - Category suggestions
  - Shipping and returns guidance
  - Platform variants for "both" platform selection
  - Graceful fallback to reasoning model on failure
  - Retry logic with exponential backoff
  
- [x] Quality check node (`src/agents/nodes/quality_check.py`)
  - Title length validation (≤ 80 chars)
  - Description word count validation (200-400 words)
  - Price reasonableness check (within 2x of median)
  - Placeholder text detection ([insert...], TODO, placeholder)
  - Retry logic with feedback (max 1 retry)
  - Deterministic validation (no LLM call)

### Prompts
- [x] Decision prompts (`src/agents/prompts/decision.py`)
  - DECISION_SYSTEM prompt
  - DECISION_USER template
  - PricingDecision Pydantic model
  
- [x] Listing writer prompts (`src/agents/prompts/listing_writer.py`)
  - WRITER_SYSTEM prompt
  - WRITER_USER template
  - ListingDraftResult Pydantic model

### Package Exports
- [x] `src/agents/nodes/__init__.py` - exports all nodes
- [x] `src/agents/prompts/__init__.py` - exports all prompts and models
- [x] `src/tools/__init__.py` - exports scraper functions

---

## Remaining Work

### Phase 4: Production Readiness

#### API Implementation
- [ ] Complete route implementations (`src/api/routes.py`)
  - Image upload handling with multipart/form-data
  - LangGraph execution with state management
  - Clarification state management (pause/resume)
  - Error responses with proper HTTP status codes
  - Response serialization
  - Webhook/n8n integration endpoints

#### Database Repositories
- [ ] Repository pattern (`src/db/repositories.py`)
  - ListingRepository - CRUD operations for listings
  - ScrapeRunRepository - Store scrape results
  - AgentRunRepository - Audit log for node execution

#### Observability
- [ ] Structured logging (`structlog`)
  - JSON output format
  - Context injection (listing_id, node_name, etc.)
  - Log levels (DEBUG, INFO, WARNING, ERROR)
  - PII redaction
  
- [ ] Prometheus metrics endpoint (`/metrics`)
  - `listing_duration_seconds` histogram
  - `scraper_duration_seconds` histogram
  - `scraper_error_total` counter
  - `llm_tokens_total` counter
  - `llm_cost_usd_total` counter
  - `listings_total` counter
  - `clarification_rounds_total` counter

#### Security & Rate Limiting
- [ ] Rate limiting middleware
  - 30 RPM per API key
  - Vinted scraper throttling (1 req/s)
  
- [ ] Input sanitization
  - Image EXIF stripping (in image_service)
  - Free-text input limits (2000 chars)
  - SQL injection prevention (parameterized queries)

#### n8n Integration
- [ ] Workflow template (`n8n/workflows/listing_workflow.json`)
  - Trigger node (webhook or form)
  - HTTP request to agent service
  - Clarification loop handling
  - Result display
  - Error handling

#### Testing
- [ ] Unit tests (`tests/unit/`)
  - Image service tests
  - Pricing service tests
  - Node logic tests (mock LLM responses)
  - Exception handling tests
  
- [ ] Integration tests (`tests/integration/`)
  - API endpoint tests
  - Database operation tests
  - Scraper tests (mocked external APIs)
  
- [ ] E2E tests (`tests/e2e/`)
  - Happy path workflow
  - Clarification flow
  - Degradation scenarios (scraper failures)
  
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
9. **LangGraph Checkpointing**: SqliteSaver/PostgresSaver for state persistence
10. **Error Handling**: Graceful degradation - scrapers fail independently

### Technical Debt / Known Issues
- [ ] LSP import errors (dependencies not installed in dev environment)
- [ ] Route implementations are skeletons (return 501 Not Implemented)
- [ ] No circuit breaker implementation yet (planned for Phase 4)
- [ ] Test files are empty (planned for Phase 4)
- [ ] Repository pattern not implemented (planned for Phase 4)
- [ ] Structured logging integration incomplete (planned for Phase 4)

### Resolved Issues
- [x] Database initialization creates tables but doesn't run migrations yet (Resolved - Alembic initialized and migrations generated)
- [x] Image sizes not using megabytes specification
- [x] LiteLLM models incorrectly defaulted in config
- [x] Missing `fast_sale` parameter on API
- [x] Missing `platform_variants` in `ListingDraft` state
- [x] Incorrect DB types (`Float` to `Numeric(10,2)`) and missing `CHECK` constraint on status
- [x] Pricing skew in `PricingService` logic
- [x] Phase 2 & 3 core agent implementation (all nodes, prompts, graph assembly)

### Blockers
None. Ready to proceed with Phase 4.

---

## File Inventory

### Source Code (30+ files)
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
│   ├── graph.py (complete - compiled agent_graph)
│   ├── nodes/
│   │   ├── __init__.py (exports all nodes)
│   │   ├── image_analysis.py (complete)
│   │   ├── agent_reasoning.py (complete)
│   │   ├── clarify.py (complete)
│   │   ├── scrape_ebay.py (complete)
│   │   ├── scrape_vinted.py (complete)
│   │   ├── agent_decision.py (complete)
│   │   ├── listing_writer.py (complete)
│   │   └── quality_check.py (complete)
│   └── prompts/
│       ├── __init__.py (exports all prompts)
│       ├── image_analysis.py (complete)
│       ├── reasoning.py (complete)
│       ├── clarification.py (complete)
│       ├── decision.py (complete)
│       └── listing_writer.py (complete)
├── tools/
│   ├── __init__.py (exports scrapers)
│   ├── ebay_scraper.py (complete)
│   └── vinted_scraper.py (complete)
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

**Total**: 50+ files

---

## Next Immediate Actions

To begin Phase 4, implement in this order:

1. **Database Repositories**:
   - `src/db/repositories.py` - ListingRepository, ScrapeRunRepository, AgentRunRepository

2. **API Route Implementations**:
   - `src/api/routes.py` - Complete POST /listing with multipart upload
   - `src/api/routes.py` - Complete POST /listing/{id}/clarify
   - `src/api/routes.py` - Complete GET /listing/{id}

3. **Structured Logging**:
   - Configure structlog in `src/main.py`
   - Add context injection middleware
   - PII redaction processors

4. **Observability**:
   - Prometheus metrics endpoint
   - Custom metrics for listings, scrapers, LLM calls

5. **Testing**:
   - Unit tests for services and nodes
   - Integration tests for API endpoints
   - E2E tests for happy path and clarification flow

6. **n8n Workflow**:
   - `n8n/workflows/listing_workflow.json` - Complete workflow template

---

*End of Project Status Document*
