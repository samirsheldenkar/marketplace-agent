# Deployment Guide

This guide covers deploying the Marketplace Listing Agent in various environments, from local development to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Local Development Deployment](#local-development-deployment)
4. [Production Deployment](#production-deployment)
5. [Cloud Deployment Options](#cloud-deployment-options)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Updating the Deployment](#updating-the-deployment)

## Prerequisites

### Required Software

- **Docker** 24.0+ and **Docker Compose** 2.20+
- **Git** (for cloning)
- **curl** or **HTTP client** (for testing)

### Required API Keys

| Service | Purpose | Get Key From |
|---------|---------|--------------|
| OpenAI | GPT-4o Vision/Reasoning | [platform.openai.com](https://platform.openai.com) |
| Apify | eBay/Vinted Scraping | [apify.com](https://apify.com) |

### System Requirements

**Minimum (Development)**:
- 4 CPU cores
- 8 GB RAM
- 20 GB disk space

**Recommended (Production)**:
- 8+ CPU cores
- 16+ GB RAM
- 100+ GB disk space (for images)

## Environment Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd marketplace-agent
```

### 2. Create Environment File

```bash
cp .env.example .env
```

### 3. Configure Environment Variables

Edit `.env` with your API keys:

```bash
# Required API Keys
OPENAI_API_KEY=sk-your-openai-key-here
MARKETPLACE_APIFY_API_TOKEN=your-apify-token-here

# LiteLLM Configuration
LITELLM_MASTER_KEY=sk-litellm-master-key-change-me

# Application API Key
MARKETPLACE_API_KEY=your-secure-api-key-here

# Database (default values work for Docker)
MARKETPLACE_DATABASE_URL=postgresql+asyncpg://marketplace:marketplace@localhost:5432/marketplace

# Optional: Custom configuration
MARKETPLACE_CONFIDENCE_THRESHOLD=0.7
MARKETPLACE_PRICE_DISCOUNT_PCT=10
MARKETPLACE_MAX_IMAGE_SIZE_MB=10
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for GPT-4o |
| `MARKETPLACE_APIFY_API_TOKEN` | Yes | - | Apify API token for scraping |
| `LITELLM_MASTER_KEY` | Yes | - | Master key for LiteLLM admin |
| `MARKETPLACE_API_KEY` | Yes | - | API key for agent service authentication |
| `MARKETPLACE_DATABASE_URL` | No | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `MARKETPLACE_LITELLM_URL` | No | `http://localhost:4000` | LiteLLM gateway URL |
| `MARKETPLACE_CONFIDENCE_THRESHOLD` | No | `0.7` | Minimum confidence for item classification |
| `MARKETPLACE_PRICE_DISCOUNT_PCT` | No | `10.0` | Default discount percentage for fast sale |
| `MARKETPLACE_MAX_IMAGE_SIZE_MB` | No | `10` | Maximum image file size |
| `MARKETPLACE_MAX_IMAGES_PER_LISTING` | No | `10` | Maximum images per listing |
| `MARKETPLACE_IMAGE_STORAGE_PATH` | No | `/tmp/marketplace_images` | Image storage path |

## Local Development Deployment

### Quick Start with Docker Compose

```bash
# Navigate to docker directory
cd docker

# Start all services in detached mode
docker-compose up -d

# Wait for services to be healthy (about 30-60 seconds)
docker-compose ps

# Check logs
docker-compose logs -f agent-service
```

### Service Endpoints

Once running, services are available at:

| Service | URL | Credentials |
|---------|-----|-------------|
| Agent API | http://localhost:8000 | API Key from `.env` |
| LiteLLM | http://localhost:4000 | Master key from `.env` |
| n8n | http://localhost:5678 | admin/admin (change in `.env`) |
| PostgreSQL | localhost:5432 | marketplace/marketplace |

### Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"0.1.0"}

# Check with API key
curl -H "Authorization: Bearer $MARKETPLACE_API_KEY" \
  http://localhost:8000/api/v1/health
```

### Development Mode (Hot Reload)

For development with code changes:

```bash
# Stop the agent-service in docker-compose
docker-compose stop agent-service

# Install local dependencies
pip install -e ".[dev]"

# Run locally with hot reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Production Deployment

### Security Checklist

Before deploying to production:

- [ ] Change default API keys (`MARKETPLACE_API_KEY`, `LITELLM_MASTER_KEY`)
- [ ] Change n8n default credentials
- [ ] Use strong PostgreSQL password
- [ ] Enable HTTPS/TLS termination
- [ ] Configure firewall rules
- [ ] Set up log aggregation
- [ ] Configure backup strategy

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${MARKETPLACE_DB_USER}
      POSTGRES_PASSWORD: ${MARKETPLACE_DB_PASSWORD}
      POSTGRES_DB: ${MARKETPLACE_DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - marketplace
    # No exposed port - internal only

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - marketplace
    # No exposed port - internal only

  litellm:
    image: ghcr.io/berriai/litellm:latest
    volumes:
      - ./litellm_config.yaml:/app/config.yaml:ro
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY}
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    networks:
      - marketplace
    # No exposed port - internal only

  agent-service:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    environment:
      MARKETPLACE_DATABASE_URL: postgresql+asyncpg://${MARKETPLACE_DB_USER}:${MARKETPLACE_DB_PASSWORD}@postgres:5432/${MARKETPLACE_DB_NAME}
      MARKETPLACE_LITELLM_URL: http://litellm:4000
      MARKETPLACE_LITELLM_API_KEY: ${LITELLM_MASTER_KEY}
      MARKETPLACE_API_KEY: ${MARKETPLACE_API_KEY}
      MARKETPLACE_APIFY_API_TOKEN: ${MARKETPLACE_APIFY_API_TOKEN}
      MARKETPLACE_IMAGE_STORAGE_PATH: /data/images
      MARKETPLACE_ENVIRONMENT: production
    volumes:
      - agent_images:/data/images
    networks:
      - marketplace
    # No exposed port - behind reverse proxy

  n8n:
    image: n8nio/n8n:latest
    environment:
      N8N_BASIC_AUTH_ACTIVE: "true"
      N8N_BASIC_AUTH_USER: ${N8N_USER}
      N8N_BASIC_AUTH_PASSWORD: ${N8N_PASSWORD}
      WEBHOOK_URL: ${N8N_WEBHOOK_URL}
    volumes:
      - n8n_data:/home/node/.n8n
    networks:
      - marketplace
    # No exposed port - behind reverse proxy

  # Reverse proxy (nginx or traefik)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - agent-service
      - n8n
    networks:
      - marketplace

volumes:
  postgres_data:
  ollama_data:
  agent_images:
  n8n_data:

networks:
  marketplace:
    driver: bridge
```

### SSL/TLS Configuration

#### Using Let's Encrypt with Nginx

```nginx
# nginx.conf snippet
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    location / {
        proxy_pass http://agent-service:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name n8n.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    location / {
        proxy_pass http://n8n:5678;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Database Backup Strategy

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

docker exec marketplace-postgres pg_dump -U marketplace marketplace > "$BACKUP_DIR/backup_$DATE.sql"

# Keep only last 7 days
find "$BACKUP_DIR" -name "backup_*.sql" -mtime +7 -delete
```

Add to crontab:
```
0 2 * * * /path/to/backup-script.sh
```

## Cloud Deployment Options

### AWS Deployment

#### Using ECS (Elastic Container Service)

1. **Create ECS Cluster**:
```bash
aws ecs create-cluster --cluster-name marketplace-agent
```

2. **Create Task Definition** (`task-definition.json`):
```json
{
  "family": "marketplace-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "8192",
  "containerDefinitions": [
    {
      "name": "agent-service",
      "image": "your-registry/marketplace-agent:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "MARKETPLACE_ENVIRONMENT", "value": "production"}
      ],
      "secrets": [
        {
          "name": "MARKETPLACE_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:..."
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/marketplace-agent",
          "awslogs-region": "us-east-1"
        }
      }
    }
  ]
}
```

3. **Deploy Service**:
```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
aws ecs create-service \
  --cluster marketplace-agent \
  --service-name agent-service \
  --task-definition marketplace-agent \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

#### Using RDS for PostgreSQL

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier marketplace-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username marketplace \
  --master-user-password your-secure-password \
  --allocated-storage 20
```

### Google Cloud Platform

#### Using Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/marketplace-agent

# Deploy to Cloud Run
gcloud run deploy marketplace-agent \
  --image gcr.io/PROJECT_ID/marketplace-agent \
  --platform managed \
  --region us-central1 \
  --set-env-vars="MARKETPLACE_ENVIRONMENT=production" \
  --set-secrets="MARKETPLACE_API_KEY=api-key:latest"
```

### Azure Deployment

#### Using Container Instances

```bash
az container create \
  --resource-group myResourceGroup \
  --name marketplace-agent \
  --image your-registry/marketplace-agent:latest \
  --cpu 4 \
  --memory 8 \
  --ports 8000 \
  --environment-variables MARKETPLACE_ENVIRONMENT=production \
  --secrets MARKETPLACE_API_KEY=your-api-key
```

## Post-Deployment Verification

### 1. Health Check

```bash
# Test health endpoint
curl https://api.yourdomain.com/health

# Should return: {"status":"healthy","services":{...}}
```

### 2. API Authentication Test

```bash
# Test with API key
curl -X POST \
  -H "Authorization: Bearer $MARKETPLACE_API_KEY" \
  -F "images=@test-image.jpg" \
  https://api.yourdomain.com/api/v1/listing
```

### 3. End-to-End Test

```bash
# Full workflow test
./scripts/e2e-test.sh
```

### 4. Monitoring Setup

Verify metrics endpoint:
```bash
curl https://api.yourdomain.com/metrics
```

Import Grafana dashboard (if applicable):
- Prometheus data source: `http://prometheus:9090`
- Dashboard JSON: `monitoring/grafana-dashboard.json`

## Updating the Deployment

### Rolling Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build agent-service
docker-compose -f docker-compose.prod.yml up -d agent-service

# Verify new version
curl https://api.yourdomain.com/health
```

### Database Migrations

```bash
# Run migrations
docker-compose exec agent-service alembic upgrade head

# Check migration status
docker-compose exec agent-service alembic current
```

### Rollback

```bash
# Rollback to previous version
docker-compose -f docker-compose.prod.yml down
git checkout <previous-tag>
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting Deployment

### Service Won't Start

```bash
# Check logs
docker-compose logs agent-service

# Check for port conflicts
sudo lsof -i :8000

# Verify environment variables
docker-compose exec agent-service env | grep MARKETPLACE
```

### Database Connection Issues

```bash
# Test database connectivity
docker-compose exec agent-service python -c "
import asyncio
from src.db.session import init_db
asyncio.run(init_db())
"

# Check PostgreSQL logs
docker-compose logs postgres
```

### LiteLLM Connection Issues

```bash
# Test LiteLLM health
curl http://localhost:4000/health

# Check LiteLLM logs
docker-compose logs litellm
```
