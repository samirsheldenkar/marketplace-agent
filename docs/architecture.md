# System Architecture

This document provides a comprehensive overview of the Marketplace Listing Agent's architecture, components, and technical design.

## High-Level Architecture

The system follows a **microservices-inspired architecture** deployed via Docker Compose, with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  (Web UI, Mobile App, n8n Workflows, API Clients)               │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP/REST
┌─────────────────────────────▼───────────────────────────────────┐
│                      API Gateway Layer                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  FastAPI Service (Port 8000)                            │   │
│  │  - Request validation                                   │   │
│  │  - Authentication (API Key)                             │   │
│  │  - Rate limiting                                        │   │
│  │  - Image handling                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                      Agent Orchestration                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LangGraph Workflow Engine                              │   │
│  │  - State management                                     │   │
│  │  - Node routing                                         │   │
│  │  - Conditional logic                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    Service Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │Image Service │  │Price Service │  │LLM Gateway   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    Data & External Services                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PostgreSQL  │  │   LiteLLM    │  │    Apify     │          │
│  │  (State DB)  │  │  (Port 4000) │  │  (Scrapers)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    Ollama    │  │    n8n       │  │ Prometheus   │          │
│  │  (Llama 3)   │  │  (Workflows) │  │  (Metrics)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Graph Structure

The core intelligence is implemented as a **LangGraph state machine** with 7 nodes:

```
START
  │
  ▼
┌──────────────────┐
│  Image Analysis  │ ── GPT-4o Vision
│  (vision_model)  │    Extract item attributes from photos
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Agent Reasoning  │ ── GPT-4o Reasoning
│ (reasoning_model)│    Build optimized search queries
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         │ (confidence < threshold)
┌────────┐    │
│Clarify │◄───┘    Ask user for clarification
└───┬────┘
    │
    ▼ (loop back)
┌──────────────────┐
│  Parallel Scraping│
├──────────────────┤
│ scrape_ebay      │ ── Apify eBay actor
│ scrape_vinted    │ ── Apify Vinted actor
└────────┬─────────┘
         │ (fan-in when both complete)
         ▼
┌──────────────────┐
│  Agent Decision  │ ── Calculate suggested price
│                  │    Determine preferred platform
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Listing Writer  │ ── Llama 3 Drafting
│ (drafting_model) │    Generate title, description
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Quality Check   │ ── Validate listing quality
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │ (quality fails, retry < 2)
    ▼         │
   END   ◄────┘ (retry listing_writer)
```

### Node Descriptions

#### 1. Image Analysis (`image_analysis`)
- **Model**: GPT-4o (vision)
- **Purpose**: Analyze uploaded photos to extract item attributes
- **Input**: List of image file paths
- **Output**: Item type, brand, model, size, color, condition, confidence score
- **Key Features**:
  - Multi-image analysis
  - Base64 encoding for API transmission
  - Graceful degradation on analysis failure

#### 2. Agent Reasoning (`agent_reasoning`)
- **Model**: GPT-4o (reasoning)
- **Purpose**: Merge image analysis with user metadata, build search queries
- **Input**: Image analysis results + user hints (brand, size, etc.)
- **Output**: Normalized attributes, eBay/Vinted search queries
- **Key Features**:
  - JSON response parsing with retry logic
  - Confidence threshold evaluation
  - Query optimization for each platform

#### 3. Clarify (`clarify`)
- **Purpose**: Request additional information when confidence is low
- **Trigger**: `confidence < MARKETPLACE_CONFIDENCE_THRESHOLD` (default: 0.7)
- **Output**: Clarification question for user
- **Behavior**: Loops back to `agent_reasoning` after user response

#### 4. Scrape eBay (`scrape_ebay`)
- **Tool**: Apify eBay Sold Listings Actor
- **Purpose**: Research comparable sold items on eBay
- **Output**: Price statistics (median, average, min, max, listings)
- **Timeout**: Configurable (default: 30s)

#### 5. Scrape Vinted (`scrape_vinted`)
- **Tool**: Apify Vinted Scraper
- **Purpose**: Research comparable items on Vinted
- **Output**: Price statistics for Vinted marketplace
- **Note**: Runs in parallel with eBay scraper

#### 6. Agent Decision (`agent_decision`)
- **Purpose**: Calculate suggested price and determine best platform
- **Logic**:
  - Calculate median across both platforms
  - Apply discount if `fast_sale=True`
  - Recommend platform based on listing volume
- **Output**: `suggested_price`, `preferred_platform`, `platform_reasoning`

#### 7. Listing Writer (`listing_writer`)
- **Model**: Llama 3 (Ollama) with GPT-4o fallback
- **Purpose**: Generate listing content
- **Output**: Title, description, categories, shipping, returns
- **Fallback**: Uses reasoning model if drafting model fails

#### 8. Quality Check (`quality_check`)
- **Purpose**: Validate generated listing quality
- **Checks**:
  - Title length and quality
  - Description completeness
  - Price reasonableness
- **Retry**: Up to 2 retries if quality fails

## Data Flow

### 1. Listing Creation Flow

```
1. Client POST /api/v1/listing
   └─> Upload images + metadata

2. FastAPI Validation
   └─> Image count, size, format validation
   └─> Store images to disk

3. Database Record Creation
   └─> Create listing with status=PENDING

4. LangGraph Execution
   └─> Invoke agent_graph.ainvoke(initial_state)

5. Node Execution (sequential as per graph)
   └─> Each node updates state
   └─> Conditional routing based on state

6. Database Update
   └─> Update listing with results
   └─> Set status=COMPLETED/CLARIFICATION/FAILED

7. Response to Client
   └─> Listing details or clarification question
```

### 2. Clarification Flow

```
1. Client POST /api/v1/listing/{id}/clarify
   └─> Submit answer to clarification question

2. State Retrieval
   └─> Load previous state from database

3. State Update
   └─> Append user message to messages
   └─> Clear needs_clarification flag

4. Re-run Agent Graph
   └─> Start from agent_reasoning node

5. Complete or Request More Clarification
   └─> Return result or new question
```

## Database Schema

### Core Tables

#### listings
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| status | Enum | PENDING, PROCESSING, COMPLETED, CLARIFICATION, FAILED |
| image_paths | JSON | Array of stored image paths |
| item_type | String | Identified item category |
| brand | String | Brand name |
| model_name | String | Model/variant |
| condition | String | New/Excellent/Good/Fair/Poor |
| confidence | Float | Analysis confidence (0.0-1.0) |
| suggested_price | Decimal | Recommended listing price |
| preferred_platform | String | ebay/vinted/both |
| platform_reasoning | Text | Why platform was chosen |
| title | String | Generated listing title |
| description | Text | Generated description |
| listing_draft | JSON | Complete draft object |
| raw_state | JSON | Full agent state snapshot |
| created_at | Timestamp | Creation time |
| updated_at | Timestamp | Last update |

## LLM Routing Strategy

The system uses **LiteLLM** as a unified gateway for model routing:

```
┌─────────────────────────────────────────────────┐
│              LiteLLM Gateway                     │
│                 (Port 4000)                      │
└──────────┬─────────────┬─────────────┬──────────┘
           │             │             │
           ▼             ▼             ▼
    ┌────────────┐ ┌──────────┐ ┌────────────┐
    │  OpenAI    │ │  Ollama  │ │  Fallback  │
    │  (GPT-4o)  │ │ (Llama3) │ │  (GPT-4o)  │
    └────────────┘ └──────────┘ └────────────┘
           │             │             │
           ▼             ▼             ▼
    Vision/Reasoning  Drafting   Drafting Fallback
```

### Model Selection

| Task | Primary Model | Fallback | Reason |
|------|---------------|----------|--------|
| Image Analysis | GPT-4o | None | Best vision capabilities |
| Reasoning | GPT-4o | None | Complex logic, JSON output |
| Drafting | Llama 3 (local) | GPT-4o | Cost-effective, no PII leak |

### Cost Optimization

- **Drafting** uses local Ollama to minimize API costs
- **Max cost per listing**: Configurable (default: $0.50)
- **Max tokens**: Configurable (default: 8000)
- **Structured output**: Reduces token waste from parsing

## Security Architecture

### Authentication
- API Key validation via `Authorization: Bearer <token>` header
- Key configurable via `MARKETPLACE_API_KEY`

### PII Protection
- Automatic PII redaction in logs (emails, phone, addresses)
- Sensitive field filtering (passwords, tokens, secrets)
- Configurable via regex patterns

### Rate Limiting
- Redis-backed rate limiting (optional)
- Default: 30 requests per minute
- Per-endpoint configuration available

### Container Security
- Non-root user (`appuser`) in production container
- Multi-stage Docker build (minimal attack surface)
- Read-only filesystem where possible

## Monitoring & Observability

### Metrics (Prometheus)
- Request latency histograms
- Listing creation duration
- Clarification round counts
- Status distribution
- LLM token usage (via LiteLLM)

### Logging (Structured)
- JSON format in production
- PII redaction
- Request context propagation (request_id, listing_id)
- Correlation IDs for distributed tracing

### Health Checks
- `/health` - Comprehensive health check
- Database connectivity
- LiteLLM gateway availability
- Individual service status

## Scalability Considerations

### Horizontal Scaling
- Stateless API layer (can run multiple instances)
- Database connection pooling
- Shared storage for images (S3-compatible in production)

### Bottlenecks
- LLM calls (rate limited by provider)
- Scraping (Apify rate limits)
- Database writes (async with connection pool)

### Caching Opportunities
- Price research results (TTL: 1 hour)
- Image analysis (if identical images)
- Popular item templates

## Integration Points

### n8n Workflows
- Webhook triggers from n8n
- Workflow definition in `n8n/workflows/`
- Automated listing pipelines

### External APIs
- **OpenAI**: GPT-4o for vision/reasoning
- **Apify**: eBay and Vinted scraping
- **LiteLLM**: Model routing and management

### File Storage
- Local filesystem (development)
- S3-compatible (production recommendation)
- Path configurable via `MARKETPLACE_IMAGE_STORAGE_PATH`

## Deployment Patterns

### Development
```
Single Docker Compose stack
All services on localhost
Hot-reload for code changes
```

### Production
```
Recommended: Kubernetes or ECS
Separate database (managed PostgreSQL)
S3 for image storage
Redis for rate limiting
Load balancer for API instances
```
