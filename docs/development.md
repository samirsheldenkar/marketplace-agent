# Development Guide

Guide for setting up a local development environment and contributing to the Marketplace Listing Agent.

## Prerequisites

- **Python** 3.11 or 3.12
- **Docker** and **Docker Compose**
- **Git**
- **Virtual environment tool** (venv, virtualenv, or conda)

## Quick Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd marketplace-agent
```

### 2. Create Virtual Environment

```bash
# Using venv
python3.11 -m venv .venv

# Activate
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Verify
which python  # Should show .venv/bin/python
```

### 3. Install Dependencies

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Verify installation
python -c "import fastapi; import langgraph; print('OK')"
```

### 4. Setup Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 5. Start Dependencies

```bash
cd docker
docker-compose up -d postgres ollama litellm

# Wait for services to be ready
docker-compose ps
```

### 6. Run Database Migrations

```bash
# From project root
alembic upgrade head
```

### 7. Start Development Server

```bash
# With hot reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or use the run script
python -m src.main
```

## Project Structure

```
marketplace-agent/
├── src/                          # Source code
│   ├── agents/                   # LangGraph agent nodes
│   │   ├── nodes/               # Individual workflow nodes
│   │   │   ├── image_analysis.py
│   │   │   ├── agent_reasoning.py
│   │   │   ├── agent_decision.py
│   │   │   ├── listing_writer.py
│   │   │   ├── quality_check.py
│   │   │   ├── clarify.py
│   │   │   ├── scrape_ebay.py
│   │   │   └── scrape_vinted.py
│   │   ├── prompts/             # LLM prompts
│   │   └── graph.py             # Graph definition
│   ├── api/                     # FastAPI application
│   │   ├── routes.py            # API endpoints
│   │   ├── schemas.py           # Pydantic models
│   │   ├── dependencies.py      # FastAPI dependencies
│   │   └── middleware.py        # Custom middleware
│   ├── db/                      # Database layer
│   │   ├── session.py           # SQLAlchemy session
│   │   └── repositories.py      # Data access layer
│   ├── models/                  # Data models
│   │   ├── state.py             # LangGraph state
│   │   └── database.py          # SQLAlchemy models
│   ├── services/                # Business logic
│   │   ├── image_service.py
│   │   └── pricing_service.py
│   ├── tools/                   # External tools
│   │   ├── ebay_scraper.py
│   │   └── vinted_scraper.py
│   ├── main.py                  # Application entry point
│   ├── config.py                # Configuration
│   └── exceptions.py            # Custom exceptions
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   ├── e2e/                     # End-to-end tests
│   └── fixtures/                # Test data
├── docker/                      # Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── litellm_config.yaml
├── docs/                        # Documentation
└── pyproject.toml               # Project configuration
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_image_service.py

# Run specific test
pytest tests/unit/test_image_service.py::test_validate_image

# Run with verbose output
pytest -v

# Run only fast tests (skip slow)
pytest -m "not slow"

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

### Code Quality

```bash
# Format code
ruff format .

# Check for linting errors
ruff check .

# Fix auto-fixable linting errors
ruff check . --fix

# Type checking
mypy src/

# Full quality check (run before committing)
ruff check . && ruff format --check . && mypy src/ && pytest
```

### Pre-commit Hooks

Setup pre-commit hooks to run checks automatically:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.2.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic
          - pydantic-settings
```

## Making Changes

### Adding a New Agent Node

1. **Create the node file** in `src/agents/nodes/`:

```python
# src/agents/nodes/my_new_node.py
import logging
from src.models.state import ListState

logger = logging.getLogger(__name__)

async def my_new_node(state: ListState) -> dict:
    """Description of what this node does."""
    logger.info("Running my_new_node")
    
    # Access state
    item_type = state.get("item_type")
    
    # Process...
    result = process_something(item_type)
    
    # Return state updates
    return {
        "new_field": result,
    }
```

2. **Add to graph** in `src/agents/graph.py`:

```python
from src.agents.nodes.my_new_node import my_new_node

# Add node
graph.add_node("my_new_node", my_new_node)

# Add edges
graph.add_edge("previous_node", "my_new_node")
graph.add_edge("my_new_node", "next_node")
```

3. **Add tests** in `tests/unit/`:

```python
# tests/unit/test_my_new_node.py
import pytest
from src.agents.nodes.my_new_node import my_new_node

@pytest.mark.asyncio
async def test_my_new_node():
    state = {
        "item_type": "headphones",
    }
    
    result = await my_new_node(state)
    
    assert "new_field" in result
    assert result["new_field"] == "expected_value"
```

### Adding a New API Endpoint

1. **Add to routes** in `src/api/routes.py`:

```python
@router.get("/my-endpoint", response_model=MyResponse)
async def my_endpoint(
    _api_key: str = Depends(verify_api_key),
) -> MyResponse:
    """My endpoint description."""
    return MyResponse(data="result")
```

2. **Add schema** in `src/api/schemas.py`:

```python
class MyResponse(BaseModel):
    """Response model for my endpoint."""
    data: str
```

3. **Add tests** in `tests/integration/test_api_endpoints.py`

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new table"

# Review the generated migration in alembic/versions/

# Apply migration
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current version
alembic current

# View migration history
alembic history
```

## Debugging

### IDE Setup (VS Code)

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["src.main:app", "--reload"],
      "jinja": true
    },
    {
      "name": "Python: pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v", "tests/unit/test_image_service.py"],
    }
  ]
}
```

### Debugging Tips

**Enable debug logging:**
```bash
# In .env
LOG_LEVEL=DEBUG
```

**Add breakpoints:**
```python
import pdb; pdb.set_trace()  # Python debugger
# or
breakpoint()  # Python 3.7+
```

**Check agent state:**
```python
# Add to any node
logger.debug("Current state", extra={"state": state})
```

**Test individual nodes:**
```python
# In a script or notebook
import asyncio
from src.agents.nodes.image_analysis import image_analysis

state = {
    "photos": ["/path/to/image.jpg"],
}

result = asyncio.run(image_analysis(state))
print(result)
```

## Common Development Tasks

### Testing Image Analysis

```python
# tests/manual/test_vision.py
import asyncio
from src.agents.nodes.image_analysis import image_analysis

async def test():
    state = {
        "photos": ["tests/fixtures/sample_item.jpg"],
    }
    result = await image_analysis(state)
    print(f"Detected: {result['item_type']}")
    print(f"Brand: {result['brand']}")
    print(f"Confidence: {result['confidence']}")

asyncio.run(test())
```

### Testing Scrapers

```python
# tests/manual/test_scrapers.py
import asyncio
from src.tools.ebay_scraper import EbayScraper
from src.config import get_settings

async def test():
    settings = get_settings()
    scraper = EbayScraper(settings.apify_api_token)
    
    results = await scraper.search("Sony WH-1000XM5")
    print(f"Found {len(results)} listings")
    for item in results[:3]:
        print(f"  - {item['title']}: £{item['price']}")

asyncio.run(test())
```

### Inspecting Database

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U marketplace -d marketplace

# Useful queries
\dt                    # List tables
\d listings            # Describe listings table
SELECT * FROM listings LIMIT 5;
SELECT status, COUNT(*) FROM listings GROUP BY status;
```

### Resetting Development Environment

```bash
# Stop all containers
docker-compose down

# Remove volumes (DELETES DATA!)
docker-compose down -v

# Rebuild containers
docker-compose build --no-cache

# Restart
docker-compose up -d

# Recreate database
alembic upgrade head
```

## Testing Strategies

### Unit Tests

Test individual functions in isolation with mocked dependencies:

```python
@pytest.mark.asyncio
async def test_pricing_service():
    settings = Mock()
    settings.price_discount_pct = 10.0
    
    service = PricingService(settings)
    
    ebay_stats = {"median_price": 100.0, "num_listings": 10}
    vinted_stats = {"median_price": 90.0, "num_listings": 5}
    
    price, platform = service.calculate_suggested_price(
        ebay_stats, vinted_stats, fast_sale=True
    )
    
    assert price == 85.5  # 95 * 0.9
    assert platform == "ebay"
```

### Integration Tests

Test API endpoints with test database:

```python
@pytest.mark.asyncio
async def test_create_listing(client: AsyncClient):
    with open("tests/fixtures/item.jpg", "rb") as f:
        response = await client.post(
            "/api/v1/listing",
            files={"images": ("item.jpg", f, "image/jpeg")},
            headers={"Authorization": "Bearer test-key"},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "listing_id" in data
    assert data["status"] == "completed"
```

### Mocking External Services

```python
import respx
from httpx import Response

@respx.mock
async def test_with_mocked_llm():
    # Mock LiteLLM response
    route = respx.post("http://localhost:4000/v1/chat/completions").mock(
        return_value=Response(200, json={
            "choices": [{"message": {"content": "{\"item_type\": \"headphones\"}"}}]
        })
    )
    
    # Run test...
    assert route.called
```

## Performance Optimization

### Profiling

```bash
# Profile a test
python -m cProfile -o profile.stats -m pytest tests/unit/test_pricing_service.py

# Analyze
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumtime'); p.print_stats(20)"
```

### Async Debugging

```python
# Check for blocking calls
import asyncio
import time

async def debug():
    start = time.time()
    await some_async_function()
    print(f"Took: {time.time() - start}s")
```

## Contributing Guidelines

### Code Style

- Follow PEP 8
- Use type hints for all functions
- Maximum line length: 88 characters
- Use double quotes for strings

### Commit Messages

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(api): add listing update endpoint

fix(agent): handle empty image analysis results

docs: update deployment guide with SSL instructions
```

### Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes with tests
3. Run full test suite: `pytest`
4. Run quality checks: `ruff check . && mypy src/`
5. Commit with descriptive messages
6. Push and create PR
7. Ensure CI passes
8. Request review

## Troubleshooting Development Issues

### Import Errors

```bash
# Ensure virtualenv is activated
which python

# Reinstall dependencies
pip install -e ".[dev]" --force-reinstall

# Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Test connection
psql postgresql://marketplace:marketplace@localhost:5432/marketplace -c "SELECT 1"
```

### Port Conflicts

```bash
# Find what's using port 8000
lsof -i :8000

# Kill process or use different port
uvicorn src.main:app --port 8001
```

### Ollama Model Not Found

```bash
# Pull the model
docker-compose exec ollama ollama pull llama3

# Verify
docker-compose exec ollama ollama list
```
