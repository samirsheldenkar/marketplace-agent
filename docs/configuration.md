# Configuration Guide

Complete reference for configuring the Marketplace Listing Agent.

## Configuration Methods

The application uses **Pydantic Settings** with the following priority (highest to lowest):

1. **Environment variables** (highest priority)
2. **`.env` file** in project root
3. **Default values** in code (lowest priority)

All environment variables use the prefix `MARKETPLACE_`.

## Core Configuration

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKETPLACE_DATABASE_URL` | `postgresql+asyncpg://localhost:5432/marketplace` | PostgreSQL connection string |
| `MARKETPLACE_DATABASE_POOL_SIZE` | `5` | Connection pool size |
| `MARKETPLACE_DATABASE_MAX_OVERFLOW` | `10` | Maximum overflow connections |

**Examples:**

```bash
# Local development
MARKETPLACE_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/marketplace

# Docker Compose (internal network)
MARKETPLACE_DATABASE_URL=postgresql+asyncpg://marketplace:marketplace@postgres:5432/marketplace

# Production (RDS, Cloud SQL, etc.)
MARKETPLACE_DATABASE_URL=postgresql+asyncpg://user:pass@db.cluster-xxx.us-east-1.rds.amazonaws.com:5432/marketplace
```

### LLM Gateway (LiteLLM)

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKETPLACE_LITELLM_URL` | `http://localhost:4000` | LiteLLM gateway URL |
| `MARKETPLACE_LITELLM_API_KEY` | `""` | API key for LiteLLM |

**Configuration:**

```bash
# Local development
MARKETPLACE_LITELLM_URL=http://localhost:4000
MARKETPLACE_LITELLM_API_KEY=sk-litellm-master-key

# Production (with load balancer)
MARKETPLACE_LITELLM_URL=http://litellm-internal:4000
```

### API Security

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKETPLACE_API_KEY` | `""` | API key for agent service authentication |
| `MARKETPLACE_API_RATE_LIMIT_RPM` | `30` | Rate limit in requests per minute |
| `MARKETPLACE_REDIS_URL` | `""` | Redis URL for distributed rate limiting |

**Examples:**

```bash
# Development
MARKETPLACE_API_KEY=dev-api-key

# Production (use strong key)
MARKETPLACE_API_KEY=mk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# With Redis rate limiting
MARKETPLACE_API_RATE_LIMIT_RPM=60
MARKETPLACE_REDIS_URL=redis://redis:6379/0
```

### External APIs

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4o |
| `MARKETPLACE_APIFY_API_TOKEN` | Yes | Apify API token for scraping |

**Obtaining API Keys:**

**OpenAI:**
1. Visit [platform.openai.com](https://platform.openai.com)
2. Create an account or sign in
3. Go to API Keys section
4. Create new secret key
5. Copy the key (starts with `sk-`)

**Apify:**
1. Visit [apify.com](https://apify.com)
2. Create an account
3. Go to Settings → API & Integrations
4. Copy your Personal API token

## Model Configuration

### Model Routing

Configure which models are used for each task:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MARKETPLACE_VISION_MODEL` | `openai/gpt-4o` | Image analysis |
| `MARKETPLACE_REASONING_MODEL` | `openai/gpt-4o` | Agent reasoning |
| `MARKETPLACE_DRAFTING_MODEL` | `ollama/llama3` | Listing generation |

**Supported Models:**

```bash
# OpenAI models
MARKETPLACE_VISION_MODEL=openai/gpt-4o
MARKETPLACE_REASONING_MODEL=openai/gpt-4o
MARKETPLACE_REASONING_MODEL=openai/gpt-4o-mini  # Cheaper alternative

# Ollama (local) models
MARKETPLACE_DRAFTING_MODEL=ollama/llama3
MARKETPLACE_DRAFTING_MODEL=ollama/llama3.1
MARKETPLACE_DRAFTING_MODEL=ollama/mistral

# Anthropic (via LiteLLM)
MARKETPLACE_REASONING_MODEL=anthropic/claude-3-sonnet-20240229

# Any LiteLLM-supported model
# See: https://docs.litellm.ai/docs/providers
```

### LiteLLM Configuration

The LiteLLM gateway configuration is in `docker/litellm_config.yaml`:

```yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  - model_name: llama3
    litellm_params:
      model: ollama/llama3
      api_base: http://ollama:11434

  - model_name: claude-3-sonnet
    litellm_params:
      model: anthropic/claude-3-sonnet-20240229
      api_key: os.environ/ANTHROPIC_API_KEY
```

**Adding New Models:**

1. Add to `docker/litellm_config.yaml`
2. Restart LiteLLM container
3. Update environment variables to use new model

## Agent Behavior

### Confidence Threshold

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKETPLACE_CONFIDENCE_THRESHOLD` | `0.7` | Minimum confidence to skip clarification |

**Adjusting:**

```bash
# More lenient (fewer clarification questions)
MARKETPLACE_CONFIDENCE_THRESHOLD=0.5

# More strict (more clarification questions)
MARKETPLACE_CONFIDENCE_THRESHOLD=0.85
```

### Pricing Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKETPLACE_PRICE_DISCOUNT_PCT` | `10.0` | Default discount % for fast sale |
| `MARKETPLACE_MAX_SCRAPER_RESULTS` | `50` | Maximum results from each scraper |
| `MARKETPLACE_SCRAPER_TIMEOUT_SECONDS` | `30` | Timeout for scraping operations |

**Examples:**

```bash
# Aggressive discount for quick sales
MARKETPLACE_PRICE_DISCOUNT_PCT=20.0

# More conservative pricing
MARKETPLACE_PRICE_DISCOUNT_PCT=5.0

# Faster scraping (fewer results)
MARKETPLACE_MAX_SCRAPER_RESULTS=20
MARKETPLACE_SCRAPER_TIMEOUT_SECONDS=15

# Slower but more thorough scraping
MARKETPLACE_MAX_SCRAPER_RESULTS=100
MARKETPLACE_SCRAPER_TIMEOUT_SECONDS=60
```

### Scraping Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKETPLACE_APIFY_EBAY_ACTOR_ID` | `caffein.dev/ebay-sold-listings` | eBay Apify actor |
| `MARKETPLACE_EBAY_COUNTRY` | `GB` | eBay marketplace country |
| `MARKETPLACE_VINTED_COUNTRY` | `GB` | Vinted marketplace country |

**Country Codes:**

```bash
# United Kingdom
MARKETPLACE_EBAY_COUNTRY=GB
MARKETPLACE_VINTED_COUNTRY=GB

# United States
MARKETPLACE_EBAY_COUNTRY=US

# Germany
MARKETPLACE_EBAY_COUNTRY=DE
MARKETPLACE_VINTED_COUNTRY=DE

# France
MARKETPLACE_EBAY_COUNTRY=FR
MARKETPLACE_VINTED_COUNTRY=FR
```

## Image Handling

### Upload Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKETPLACE_MAX_IMAGE_SIZE_MB` | `10` | Maximum image file size in MB |
| `MARKETPLACE_MAX_IMAGES_PER_LISTING` | `10` | Maximum images per listing |
| `MARKETPLACE_ALLOWED_IMAGE_FORMATS` | `["jpg","jpeg","png","webp","heic"]` | Allowed formats |

**Examples:**

```bash
# Allow larger images
MARKETPLACE_MAX_IMAGE_SIZE_MB=20

# More images per listing
MARKETPLACE_MAX_IMAGES_PER_LISTING=15

# Restrict formats
MARKETPLACE_ALLOWED_IMAGE_FORMATS=["jpg","png"]
```

### Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKETPLACE_IMAGE_STORAGE_PATH` | `/data/images` | Path for storing images |

**Examples:**

```bash
# Local development
MARKETPLACE_IMAGE_STORAGE_PATH=/tmp/marketplace_images

# Docker volume
MARKETPLACE_IMAGE_STORAGE_PATH=/data/images

# Production (S3 or persistent disk)
MARKETPLACE_IMAGE_STORAGE_PATH=/var/lib/marketplace/images
```

**Note:** For S3 storage, modify `src/services/image_service.py` to use boto3.

## Cost Controls

### LLM Usage Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKETPLACE_MAX_TOKENS_PER_LISTING` | `8000` | Maximum tokens per listing |
| `MARKETPLACE_MAX_LLM_COST_PER_LISTING_USD` | `0.50` | Maximum cost per listing |

**Examples:**

```bash
# Strict cost control
MARKETPLACE_MAX_LLM_COST_PER_LISTING_USD=0.25
MARKETPLACE_MAX_TOKENS_PER_LISTING=4000

# Allow more expensive listings
MARKETPLACE_MAX_LLM_COST_PER_LISTING_USD=1.00
MARKETPLACE_MAX_TOKENS_PER_LISTING=12000
```

## Network Configuration

### API Server

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKETPLACE_API_HOST` | `0.0.0.0` | API server bind host |
| `MARKETPLACE_API_PORT` | `8000` | API server port |

**Examples:**

```bash
# Bind to localhost only (more secure)
MARKETPLACE_API_HOST=127.0.0.1

# Custom port
MARKETPLACE_API_PORT=8080
```

## Environment-Specific Configuration

### Development

```bash
# .env.development
MARKETPLACE_ENVIRONMENT=development
MARKETPLACE_DATABASE_URL=postgresql+asyncpg://marketplace:marketplace@localhost:5432/marketplace
MARKETPLACE_LITELLM_URL=http://localhost:4000
MARKETPLACE_API_KEY=dev-api-key
MARKETPLACE_CONFIDENCE_THRESHOLD=0.6
MARKETPLACE_PRICE_DISCOUNT_PCT=10.0
```

### Staging

```bash
# .env.staging
MARKETPLACE_ENVIRONMENT=staging
MARKETPLACE_DATABASE_URL=postgresql+asyncpg://user:pass@staging-db:5432/marketplace
MARKETPLACE_LITELLM_URL=http://litellm-staging:4000
MARKETPLACE_API_KEY=staging-api-key-change-me
MARKETPLACE_CONFIDENCE_THRESHOLD=0.7
MARKETPLACE_API_RATE_LIMIT_RPM=60
```

### Production

```bash
# .env.production
MARKETPLACE_ENVIRONMENT=production
MARKETPLACE_DATABASE_URL=postgresql+asyncpg://user:pass@prod-db.cluster-xxx.us-east-1.rds.amazonaws.com:5432/marketplace
MARKETPLACE_LITELLM_URL=http://litellm-internal:4000
MARKETPLACE_API_KEY=mk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MARKETPLACE_API_RATE_LIMIT_RPM=30
MARKETPLACE_CONFIDENCE_THRESHOLD=0.75
MARKETPLACE_MAX_IMAGE_SIZE_MB=10
MARKETPLACE_IMAGE_STORAGE_PATH=/data/images
MARKETPLACE_REDIS_URL=redis://prod-redis:6379
```

## Logging Configuration

### Structured Logging

The application uses `structlog` for structured logging. Configure via environment:

```bash
# Development (pretty console output)
MARKETPLACE_ENVIRONMENT=development

# Production (JSON output)
MARKETPLACE_ENVIRONMENT=production
```

### PII Redaction

PII is automatically redacted from logs. Patterns include:
- Email addresses
- Phone numbers
- Social Security Numbers
- Credit card numbers
- Physical addresses

Sensitive field names are also redacted:
- password, token, secret, api_key
- authorization, credit_card, ssn

**Note:** PII redaction is always enabled and cannot be disabled.

## Configuration Validation

The application validates configuration on startup. Invalid configuration will prevent the application from starting.

### Required Validation

- `MARKETPLACE_DATABASE_URL` must be a valid PostgreSQL URL
- `MARKETPLACE_LITELLM_URL` must be a valid HTTP URL
- `MARKETPLACE_CONFIDENCE_THRESHOLD` must be between 0.0 and 1.0
- `MARKETPLACE_PRICE_DISCOUNT_PCT` must be between 0.0 and 100.0
- `MARKETPLACE_API_PORT` must be a valid port number (1-65535)

### Startup Errors

```
# Example: Missing required API key
ERROR: Configuration error: MARKETPLACE_APIFY_API_TOKEN is required

# Example: Invalid confidence threshold
ERROR: Configuration error: MARKETPLACE_CONFIDENCE_THRESHOLD must be between 0.0 and 1.0

# Example: Invalid database URL
ERROR: Configuration error: MARKETPLACE_DATABASE_URL is not a valid PostgreSQL URL
```

## Advanced Configuration

### Custom Apify Actors

You can use custom Apify actors for scraping:

```bash
# Custom eBay actor
MARKETPLACE_APIFY_EBAY_ACTOR_ID=your-username/your-ebay-actor

# Requires the actor to return compatible output format
```

### Model Fallbacks

Configure fallback models in `docker/litellm_config.yaml`:

```yaml
model_list:
  - model_name: primary-gpt4
    litellm_params:
      model: openai/gpt-4o
    fallback_models:
      - gpt-4o-mini
      - claude-3-sonnet
```

### Caching Configuration

To enable response caching for identical requests:

```yaml
# docker/litellm_config.yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      caching: true
caching:
  type: redis
  host: redis
  port: 6379
```

## Configuration File Reference

### .env

```bash
# API Keys (REQUIRED)
OPENAI_API_KEY=sk-your-openai-key
MARKETPLACE_APIFY_API_TOKEN=your-apify-token
LITELLM_MASTER_KEY=your-litellm-master-key
MARKETPLACE_API_KEY=your-api-key

# Database
MARKETPLACE_DATABASE_URL=postgresql+asyncpg://marketplace:marketplace@localhost:5432/marketplace

# LLM Gateway
MARKETPLACE_LITELLM_URL=http://localhost:4000
MARKETPLACE_LITELLM_API_KEY=sk-litellm-master

# Models
MARKETPLACE_VISION_MODEL=openai/gpt-4o
MARKETPLACE_REASONING_MODEL=openai/gpt-4o
MARKETPLACE_DRAFTING_MODEL=ollama/llama3

# Agent Behavior
MARKETPLACE_CONFIDENCE_THRESHOLD=0.7
MARKETPLACE_PRICE_DISCOUNT_PCT=10.0
MARKETPLACE_MAX_SCRAPER_RESULTS=50
MARKETPLACE_SCRAPER_TIMEOUT_SECONDS=30

# Scraping
MARKETPLACE_APIFY_EBAY_ACTOR_ID=caffein.dev/ebay-sold-listings
MARKETPLACE_EBAY_COUNTRY=GB
MARKETPLACE_VINTED_COUNTRY=GB

# Image Handling
MARKETPLACE_MAX_IMAGE_SIZE_MB=10
MARKETPLACE_MAX_IMAGES_PER_LISTING=10
MARKETPLACE_ALLOWED_IMAGE_FORMATS=["jpg","jpeg","png","webp","heic"]
MARKETPLACE_IMAGE_STORAGE_PATH=/data/images

# Cost Controls
MARKETPLACE_MAX_TOKENS_PER_LISTING=8000
MARKETPLACE_MAX_LLM_COST_PER_LISTING_USD=0.50

# API Server
MARKETPLACE_API_HOST=0.0.0.0
MARKETPLACE_API_PORT=8000
MARKETPLACE_API_RATE_LIMIT_RPM=30
MARKETPLACE_REDIS_URL=
```
