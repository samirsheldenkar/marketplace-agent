# Troubleshooting Guide

Common issues and solutions for the Marketplace Listing Agent.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Startup Issues](#startup-issues)
- [API Errors](#api-errors)
- [Agent Workflow Issues](#agent-workflow-issues)
- [LLM Issues](#llm-issues)
- [Scraping Issues](#scraping-issues)
- [Database Issues](#database-issues)
- [Performance Issues](#performance-issues)
- [Docker Issues](#docker-issues)

## Installation Issues

### pip install fails with "No module named 'src'"

**Problem:** Installing in editable mode fails.

**Solution:**
```bash
# Ensure you're in the project root
pwd  # Should show .../marketplace-agent

# Use the correct command
pip install -e ".[dev]"

# Or install without editable mode
pip install .
```

### ImportError: cannot import name 'ListState'

**Problem:** Python can't find modules.

**Solution:**
```bash
# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in editable mode
pip install -e ".[dev]"
```

## Startup Issues

### Service fails to start: "ModuleNotFoundError"

**Problem:** Dependencies not installed.

**Solution:**
```bash
# Install dependencies
pip install -e ".[dev]"

# Verify installation
python -c "import src.main; print('OK')"
```

### Application starts but returns 500 errors

**Problem:** Database not initialized.

**Solution:**
```bash
# Run migrations
alembic upgrade head

# Check database connection
python -c "
import asyncio
from src.db.session import init_db
asyncio.run(init_db())
"
```

### "Address already in use" error

**Problem:** Port 8000 is in use.

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000
# or
netstat -tlnp | grep 8000

# Kill the process
kill -9 <PID>

# Or use different port
uvicorn src.main:app --port 8001
```

## API Errors

### 401 Unauthorized

**Problem:** Missing or invalid API key.

**Solution:**
```bash
# Check API key is set
echo $MARKETPLACE_API_KEY

# Include in request
curl -H "Authorization: Bearer $MARKETPLACE_API_KEY" \
  http://localhost:8000/api/v1/listing

# Verify in .env file
grep MARKETPLACE_API_KEY .env
```

### 400 Bad Request - "Maximum 10 images allowed"

**Problem:** Too many images uploaded.

**Solution:**
```bash
# Limit to 10 images
curl -F "images=@1.jpg" -F "images=@2.jpg" ...  # up to 10

# Or increase limit in .env
MARKETPLACE_MAX_IMAGES_PER_LISTING=15
```

### 400 Bad Request - "Invalid image format"

**Problem:** Image format not supported.

**Solution:**
```bash
# Supported formats: jpg, jpeg, png, webp, gif
# Convert image
convert image.bmp image.jpg

# Or add format to allowed list in .env
MARKETPLACE_ALLOWED_IMAGE_FORMATS=["jpg","jpeg","png","webp","gif","bmp"]
```

### 503 Service Unavailable - "LLM gateway unavailable"

**Problem:** LiteLLM is not running or unreachable.

**Solution:**
```bash
# Check LiteLLM status
curl http://localhost:4000/health

# Check LiteLLM logs
docker-compose logs litellm

# Restart LiteLLM
docker-compose restart litellm

# Verify configuration
env | grep LITELLM
```

### 503 Service Unavailable - "Marketplace scrapers unavailable"

**Problem:** Apify token is missing or invalid.

**Solution:**
```bash
# Check token is set
echo $MARKETPLACE_APIFY_API_TOKEN

# Test Apify connection
curl -H "Authorization: Bearer $MARKETPLACE_APIFY_API_TOKEN" \
  https://api.apify.com/v2/acts
```

## Agent Workflow Issues

### Listing stuck in "processing" status

**Problem:** Agent graph execution failed silently.

**Solution:**
```bash
# Check application logs
docker-compose logs -f agent-service

# Check for errors in logs
grep ERROR logs/app.log

# Restart the service
docker-compose restart agent-service
```

### Always asks for clarification

**Problem:** Confidence threshold too high or image analysis failing.

**Solution:**
```bash
# Lower confidence threshold
MARKETPLACE_CONFIDENCE_THRESHOLD=0.5

# Check image quality
# - Ensure good lighting
# - Show the full item
# - Include multiple angles

# Test image analysis manually
python -c "
import asyncio
from src.agents.nodes.image_analysis import image_analysis
result = asyncio.run(image_analysis({'photos': ['test.jpg']}))
print(result)
"
```

### Price seems too high/low

**Problem:** Scraper not finding comparable items.

**Solution:**
```bash
# Check scraper is working
python -c "
import asyncio
from src.tools.ebay_scraper import EbayScraper
from src.config import get_settings
settings = get_settings()
scraper = EbayScraper(settings.apify_api_token)
results = asyncio.run(scraper.search('Sony WH-1000XM5'))
print(f'Found {len(results)} results')
"

# Adjust search terms manually in clarifications
```

### Listing quality is poor

**Problem:** Drafting model producing suboptimal output.

**Solution:**
```bash
# Switch to GPT-4o for drafting
MARKETPLACE_DRAFTING_MODEL=openai/gpt-4o

# Or improve prompts in src/agents/prompts/listing_writer.py
```

## LLM Issues

### OpenAI API errors

**Problem:** Invalid API key or rate limiting.

**Solution:**
```bash
# Test OpenAI connection
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check quota at platform.openai.com

# Try a different model
MARKETPLACE_VISION_MODEL=openai/gpt-4o-mini
```

### Ollama connection errors

**Problem:** Ollama not running or model not pulled.

**Solution:**
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Pull the model
docker-compose exec ollama ollama pull llama3

# List available models
docker-compose exec ollama ollama list

# Check Ollama logs
docker-compose logs ollama
```

### "Model not found" errors

**Problem:** Model not configured in LiteLLM.

**Solution:**
```bash
# Check LiteLLM config
cat docker/litellm_config.yaml

# Verify model routing
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"

# Add model to config if missing
```

### High LLM costs

**Problem:** Too many tokens being used.

**Solution:**
```bash
# Set cost limits
MARKETPLACE_MAX_LLM_COST_PER_LISTING_USD=0.25
MARKETPLACE_MAX_TOKENS_PER_LISTING=4000

# Use cheaper models
MARKETPLACE_REASONING_MODEL=openai/gpt-4o-mini
MARKETPLACE_DRAFTING_MODEL=ollama/llama3

# Monitor usage
curl http://localhost:4000/spend/logs \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

## Scraping Issues

### No eBay results found

**Problem:** Apify actor not working or item too obscure.

**Solution:**
```bash
# Test Apify connection
curl -H "Authorization: Bearer $MARKETPLACE_APIFY_API_TOKEN" \
  https://api.apify.com/v2/acts/caffein.dev~ebay-sold-listings/runs

# Check Apify console for errors
# https://console.apify.com/actors/runs

# Try different search terms in clarifications
```

### Vinted scraper timeout

**Problem:** Vinted blocking scraper or rate limiting.

**Solution:**
```bash
# Increase timeout
MARKETPLACE_SCRAPER_TIMEOUT_SECONDS=60

# Reduce max results
MARKETPLACE_MAX_SCRAPER_RESULTS=20

# Check Vinted is accessible from your region
```

### Apify rate limit exceeded

**Problem:** Too many requests to Apify.

**Solution:**
```bash
# Check Apify limits at console.apify.com

# Add delays between requests (requires code change)

# Upgrade Apify plan for higher limits
```

## Database Issues

### "Connection refused" to PostgreSQL

**Problem:** PostgreSQL not running or wrong connection string.

**Solution:**
```bash
# Check PostgreSQL status
docker-compose ps postgres

# Start PostgreSQL
docker-compose up -d postgres

# Check connection string
echo $MARKETPLACE_DATABASE_URL

# Test connection
docker-compose exec postgres pg_isready -U marketplace
```

### Migration errors

**Problem:** Database schema out of sync.

**Solution:**
```bash
# Check current version
alembic current

# View history
alembic history

# Downgrade and re-upgrade
alembic downgrade -1
alembic upgrade head

# Or reset (DELETES DATA!)
docker-compose down -v
docker-compose up -d postgres
alembic upgrade head
```

### "Table does not exist" errors

**Problem:** Migrations not applied.

**Solution:**
```bash
# Run migrations
alembic upgrade head

# Check if tables exist
docker-compose exec postgres psql -U marketplace -d marketplace -c "\dt"
```

## Performance Issues

### Slow listing creation (>60 seconds)

**Problem:** Scraping or LLM calls are slow.

**Solutions:**

1. **Check scraper performance:**
```bash
# Reduce timeout to fail faster
MARKETPLACE_SCRAPER_TIMEOUT_SECONDS=20

# Reduce results
MARKETPLACE_MAX_SCRAPER_RESULTS=20
```

2. **Use local models:**
```bash
# Ensure Ollama is working
curl http://localhost:11434/api/tags

# Check GPU acceleration
docker-compose exec ollama nvidia-smi  # If using GPU
```

3. **Monitor timing:**
```bash
# Enable detailed logging
LOG_LEVEL=DEBUG

# Check metrics
curl http://localhost:8000/metrics
```

### High memory usage

**Problem:** Too many concurrent requests or memory leak.

**Solution:**
```bash
# Limit concurrent requests (add to docker-compose)
environment:
  - WEB_CONCURRENCY=2

# Restart containers periodically
docker-compose restart

# Monitor memory
docker stats
```

### Database connection pool exhausted

**Problem:** Too many concurrent connections.

**Solution:**
```bash
# Increase pool size
MARKETPLACE_POOL_SIZE=10
MARKETPLACE_MAX_OVERFLOW=20

# Check active connections
docker-compose exec postgres psql -U marketplace -c "
SELECT count(*) FROM pg_stat_activity;
"
```

## Docker Issues

### Container fails to start

**Problem:** Various configuration issues.

**Solution:**
```bash
# Check logs
docker-compose logs <service-name>

# Rebuild containers
docker-compose build --no-cache

# Check environment file
cat .env

# Validate docker-compose
docker-compose config
```

### "Bind for 0.0.0.0:8000 failed" 

**Problem:** Port already in use.

**Solution:**
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9

# Or change port in docker-compose.yml
ports:
  - "8001:8000"
```

### Volume permission errors

**Problem:** User permissions in container.

**Solution:**
```bash
# Fix image storage permissions
sudo chown -R 1000:1000 /path/to/image/storage

# Or run with privileged mode (development only)
docker-compose exec --privileged agent-service bash
```

### Images not persisting

**Problem:** Volume not mounted correctly.

**Solution:**
```bash
# Check volume mounts
docker-compose config | grep volumes -A 10

# Verify volume exists
docker volume ls | grep marketplace

# Check container can write
docker-compose exec agent-service touch /data/images/test.txt
```

## Getting Help

### Gather Diagnostic Information

```bash
#!/bin/bash
# diagnostic.sh

echo "=== Environment ==="
env | grep MARKETPLACE | sort

echo ""
echo "=== Docker Status ==="
docker-compose ps

echo ""
echo "=== Recent Logs ==="
docker-compose logs --tail=50 agent-service

echo ""
echo "=== Health Check ==="
curl -s http://localhost:8000/health | jq .

echo ""
echo "=== Database ==="
docker-compose exec -T postgres psql -U marketplace -c "SELECT COUNT(*), status FROM listings GROUP BY status;"

echo ""
echo "=== LiteLLM Health ==="
curl -s http://localhost:4000/health
```

### Check Service Dependencies

```bash
# Test all services
#!/bin/bash

echo "Testing API..."
curl -s http://localhost:8000/health | jq .status

echo "Testing LiteLLM..."
curl -s http://localhost:4000/health | jq .status

echo "Testing PostgreSQL..."
docker-compose exec -T postgres pg_isready -U marketplace

echo "Testing Ollama..."
curl -s http://localhost:11434/api/tags | jq '.models | length'
```

### Enable Debug Logging

```python
# Add to src/main.py temporarily
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment variable
LOG_LEVEL=DEBUG
```

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Service not running | Start the service with docker-compose |
| `Invalid API key` | Wrong or missing API key | Check MARKETPLACE_API_KEY |
| `Timeout` | Operation took too long | Increase timeout or check service health |
| `Rate limit exceeded` | Too many requests | Wait and retry, or increase rate limit |
| `Table does not exist` | Migrations not run | Run `alembic upgrade head` |
| `No module named 'xxx'` | Missing dependency | Run `pip install -e ".[dev]"` |
| `Permission denied` | File permissions | Check and fix permissions |
| `Address already in use` | Port conflict | Kill process or change port |
| `Model not found` | Model not in LiteLLM config | Add model to litellm_config.yaml |

## Reporting Issues

When reporting issues, include:

1. **Environment:**
   - OS and version
   - Docker version
   - Python version

2. **Configuration:**
   - Relevant environment variables (redact secrets)
   - Docker Compose configuration

3. **Logs:**
   - Application logs
   - Error messages
   - Stack traces

4. **Reproduction:**
   - Steps to reproduce
   - Sample request/data
   - Expected vs actual behavior
