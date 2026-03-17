# Agent Guidelines for Hybrid eBay/Vinted Listing Agent

This document provides essential guidance for AI agents working on this Python-based marketplace listing agent codebase.

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI + LangGraph (agent orchestration)
- **LLM Gateway**: LiteLLM (OpenAI + Ollama routing)
- **Database**: PostgreSQL
- **Deployment**: Docker
- **Workflow**: n8n integration

## Build / Test / Lint Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run single test file
pytest tests/test_listing_agent.py

# Run single test
pytest tests/test_listing_agent.py::test_analyze_images -v

# Type checking
mypy src/

# Linting and formatting (ruff handles both)
ruff check .                 # Check for issues
ruff check . --fix          # Auto-fix issues
ruff format .               # Format code

# Full quality check (run before committing)
ruff check . && ruff format --check . && mypy src/ && pytest
```

## Code Style Guidelines

### Imports

Order: stdlib → third-party → local, separated by blank lines:

```python
import json
from typing import Optional

from fastapi import FastAPI
from langgraph.graph import StateGraph

from src.tools.ebay_scraper import EbayScraper
from src.models.state import ListState
```

### Formatting

- **Line length**: 88 characters (Black-compatible)
- **Quotes**: Double quotes for strings
- **Trailing commas**: Required for multi-line collections
- Use `ruff format` for auto-formatting

### Type Hints

- Use type hints for all function parameters and return types
- Use `Optional[X]` instead of `X | None` for compatibility
- Use Pydantic models for API request/response schemas
- Enable strict mypy: `mypy --strict src/`

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Modules | snake_case | `ebay_scraper.py` |
| Classes | PascalCase | `ListingAgent` |
| Functions | snake_case | `analyze_images()` |
| Constants | UPPER_SNAKE | `MAX_RETRIES = 3` |
| Variables | snake_case | `price_stats` |
| Private | _leading_underscore | `_fetch_with_retry()` |

### Error Handling

- Use custom exception classes in `src/exceptions.py`:
  - `ScraperError` – scraper failures
  - `LLMError` – LLM gateway issues
  - `ValidationError` – input validation failures

- Always catch specific exceptions, log context, and wrap when propagating:

```python
from src.exceptions import ScraperError

async def fetch_ebay_listings(query: str) -> dict:
    try:
        return await scraper.search(query)
    except TimeoutError as e:
        logger.warning("eBay scraper timeout", query=query)
        raise ScraperError(f"eBay timeout for query: {query}") from e
```

- Use `structlog` for structured logging with context

### LangGraph Patterns

- Define state as TypedDict in `src/models/state.py`
- Keep nodes pure – accept state, return updates
- Use `ToolNode` for external tool calls
- Document graph transitions with comments

```python
async def agent_reasoning(state: ListState) -> dict:
    """Analyze item and trigger scraper calls."""
    # Implementation here
    return {"item_type": "headphones", "confidence": 0.92}
```

### FastAPI Patterns

- Use dependency injection for shared resources
- Return Pydantic response models
- Handle errors with HTTPException and custom handlers
- Document endpoints with summary and response_model

```python
@app.post("/listing", response_model=ListingResponse)
async def create_listing(request: ListingRequest) -> ListingResponse:
    """Start a listing analysis workflow."""
    pass
```

### Environment & Config

- Use Pydantic Settings for configuration
- Load from `.env` file in development
- Never commit secrets – use Docker secrets or env vars

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    litellm_url: str = "http://litellm:4000"
    
    class Config:
        env_file = ".env"
```

### Testing

- Use `pytest-asyncio` for async tests
- Mock external services (scrapers, LLM calls)
- Use factories (factory-boy) for test data
- Target >80% coverage for business logic

```python
@pytest.mark.asyncio
async def test_analyze_images(mock_vision_model):
    result = await analyze_images(["photo.jpg"])
    assert result.confidence > 0.5
```

## Project Structure

```
src/
├── api/              # FastAPI routes
├── agents/           # LangGraph nodes and graphs
├── tools/            # Scraper tools (eBay, Vinted)
├── models/           # Pydantic models and state
├── services/         # Business logic
├── exceptions.py     # Custom exceptions
└── config.py         # Settings

tests/
├── unit/             # Unit tests
├── integration/      # Integration tests
└── fixtures/         # Test data
```

## Key Rules

1. **Never expose PII in logs** – redact user data
2. **Handle scraper failures gracefully** – degrade with available data
3. **Tag LLM calls** – use `reasoning` or `drafting` for LiteLLM routing
4. **Validate all external inputs** – use Pydantic schemas
5. **Keep functions small** – single responsibility, <50 lines
