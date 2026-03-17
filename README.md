# Hybrid eBay/Vinted Listing Agent

A self-hosted Python AI agent that analyzes item photos, researches comparable prices on eBay and Vinted, and generates optimized listing drafts with pricing recommendations.

## Architecture

- **LangGraph** agent with 7 nodes for orchestration
- **LiteLLM** gateway for model-agnostic LLM routing (GPT-4o for vision/reasoning, Ollama/Llama 3 for drafting)
- **FastAPI** for the API service
- **PostgreSQL** for data persistence
- **n8n** for workflow automation

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repo>
   cd marketplace-agent
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start with Docker**:
   ```bash
   cd docker
   docker-compose up -d
   ```

3. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

4. **Access services**:
   - Agent API: http://localhost:8000
   - n8n: http://localhost:5678
   - LiteLLM: http://localhost:4000

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check . && ruff format .

# Type checking
mypy src/
```

## License

MIT
