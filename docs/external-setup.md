# External Services Setup Guide

This guide covers deploying the Marketplace Listing Agent when LiteLLM, Ollama, and n8n are running on separate machines connected via Tailscale.

## Architecture Overview

```
VPS A (n8n + Agent Service + PostgreSQL) ←──Tailscale──→ VPS B (LiteLLM + Ollama)

┌─────────────────────────────────────────────────────────────────────────────┐
│                                    VPS A                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │
│  │  FastAPI Agent  │◄──►│      n8n        │    │      PostgreSQL         │ │
│  │    Service      │    │  (localhost)    │    │    (Docker network)     │ │
│  │   (:8000)       │    │   (:5678)       │    │                         │ │
│  └────────┬────────┘    └─────────────────┘    └─────────────────────────┘ │
│           │                                                                  │
│           │  Tailscale Network (100.x.x.x/10)                                │
│           │                                                                  │
└───────────┼──────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                    VPS B                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         LiteLLM Gateway (:4000)                          ││
│  │  • API key validation    • Rate limiting    • Model routing              ││
│  │  • Routes to Ollama on same network                                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                   │                                         │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                           Ollama (:11434)                                ││
│  │  • Local LLM (llama3, etc.)                                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Tailscale** installed and configured on all machines
2. **LiteLLM** running on VPS B with:
   - Authentication enabled (master key)
   - Ollama configured as a backend
   - Accessible from VPS A via Tailscale IP
3. **n8n** running on VPS A (self-hosted)
4. **Docker** and **Docker Compose** on VPS A

## Setup Instructions

### Step 1: Find Tailscale IPs

On each machine, get the Tailscale IP:

```bash
tailscale ip -4
# Example output: 100.64.0.1
```

Note the IP for your LiteLLM machine (VPS B).

### Step 2: Configure LiteLLM (VPS B)

Ensure your `litellm_config.yaml` has Ollama properly configured:

```yaml
model_list:
  - model_name: drafting
    litellm_params:
      model: ollama/llama3
      api_base: http://localhost:11434  # Ollama on same machine
      max_tokens: 4096
      temperature: 0.7

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

Verify LiteLLM is accessible from VPS A:

```bash
# On VPS A
curl http://100.x.x.x:4000/health \
  -H "Authorization: Bearer your-litellm-api-key"
```

### Step 3: Deploy Agent Service (VPS A)

1. **Clone the repository:**

```bash
cd /opt
git clone <repository-url>
cd marketplace-agent
```

2. **Create environment file:**

```bash
cp .env.external.example .env
nano .env
```

Edit the following values:

```bash
# Database (generate a strong password)
MARKETPLACE_DB_PASSWORD=your-secure-db-password

# LiteLLM (use the Tailscale IP from Step 1)
MARKETPLACE_LITELLM_URL=http://100.x.x.x:4000
MARKETPLACE_LITELLM_API_KEY=sk-litellm-your-key-here

# API Key for n8n (generate with: openssl rand -hex 32)
MARKETPLACE_API_KEY=your-secure-api-key-here

# Apify (if using eBay scraping)
MARKETPLACE_APIFY_API_TOKEN=your-apify-token
```

3. **Start the services:**

```bash
cd docker
docker-compose -f docker-compose.external.yml up -d
```

4. **Verify the deployment:**

```bash
# Check service health
curl http://localhost:8000/health

# Expected output:
# {
#   "status": "healthy",
#   "services": {
#     "database": {"status": "healthy"},
#     "litellm": {"status": "healthy"}
#   }
# }
```

### Step 4: Configure n8n (VPS A)

1. **Set environment variables in n8n:**

Go to **Settings** → **External Storage** → **Environment** (or set via your n8n deployment method):

```bash
AGENT_SERVICE_URL=http://localhost:8000
AGENT_API_KEY=your-secure-api-key-here  # Same as MARKETPLACE_API_KEY above
```

2. **Import the workflow:**

- Open n8n
- Go to **Workflows** → **Import from File**
- Select `n8n/workflows/listing_workflow_external.json`
- Activate the workflow

3. **Test the connection:**

- Open the **Create Listing** node
- Click **Test** to verify n8n can reach the agent service

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MARKETPLACE_DB_PASSWORD` | Yes | - | PostgreSQL password |
| `MARKETPLACE_LITELLM_URL` | Yes | - | Tailscale IP of LiteLLM |
| `MARKETPLACE_LITELLM_API_KEY` | Yes | - | LiteLLM API key |
| `MARKETPLACE_API_KEY` | Yes | - | API key for n8n authentication |
| `MARKETPLACE_APIFY_API_TOKEN` | No | - | Apify token for eBay scraping |
| `MARKETPLACE_DB_USER` | No | `marketplace` | PostgreSQL username |
| `MARKETPLACE_DB_NAME` | No | `marketplace` | PostgreSQL database name |

### n8n Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `AGENT_SERVICE_URL` | `http://localhost:8000` | URL where n8n can reach agent service |
| `AGENT_API_KEY` | Same as `MARKETPLACE_API_KEY` | Authentication key |

## Troubleshooting

### Agent Service Can't Reach LiteLLM

```bash
# Test connectivity from VPS A to VPS B via Tailscale
ping 100.x.x.x

# Test LiteLLM specifically
curl -v http://100.x.x.x:4000/health \
  -H "Authorization: Bearer your-litellm-api-key"

# Check Tailscale status
tailscale status
```

**Common issues:**
- Firewall blocking port 4000 on VPS B
- LiteLLM not binding to Tailscale interface (should bind to `0.0.0.0`)
- Wrong API key

### n8n Can't Reach Agent Service

```bash
# From VPS A (same machine as n8n)
curl http://localhost:8000/health

# Check if agent service is bound to all interfaces
docker-compose -f docker-compose.external.yml logs agent-service
```

**Common issues:**
- Agent service not running
- Port 8000 not exposed or bound to wrong interface
- Wrong `AGENT_SERVICE_URL` in n8n

### Database Connection Issues

```bash
# Check PostgreSQL container
docker-compose -f docker-compose.external.yml logs postgres

# Verify database URL format
# Should be: postgresql+asyncpg://user:pass@postgres:5432/dbname
```

## Security Considerations

1. **Tailscale provides encryption** between VPSs - no additional TLS needed for internal traffic
2. **API keys are required** for both LiteLLM and agent service authentication
3. **PostgreSQL is not exposed** - only accessible within Docker network
4. **Agent service binds to 0.0.0.0** but only n8n on the same machine should access it

### Optional: Restrict Agent Service to Localhost Only

If you want to ensure only n8n (localhost) can reach the agent service:

```yaml
# docker-compose.external.yml
services:
  agent-service:
    ports:
      - "127.0.0.1:8000:8000"  # Only localhost, not 0.0.0.0
```

Then in n8n, use `AGENT_SERVICE_URL=http://localhost:8000` (this is already the default).

## Maintenance

### View Logs

```bash
docker-compose -f docker-compose.external.yml logs -f agent-service
docker-compose -f docker-compose.external.yml logs -f postgres
```

### Update the Service

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose -f docker-compose.external.yml up -d --build agent-service
```

### Backup PostgreSQL

```bash
docker-compose -f docker-compose.external.yml exec postgres \
  pg_dump -U marketplace marketplace > backup.sql
```

## Migration from All-in-One Setup

If you're migrating from the standard Docker Compose setup:

1. **Backup your database** (if you want to keep data)
2. **Stop old services:** `docker-compose down`
3. **Switch to external compose:** Use `docker-compose.external.yml`
4. **Update environment variables** in `.env`
5. **Start new services:** `docker-compose -f docker-compose.external.yml up -d`
6. **Update n8n workflow** to use the external version

## Support

For issues specific to this external services setup:
- Check the [main troubleshooting guide](./troubleshooting.md)
- Verify Tailscale connectivity: `tailscale status` and `tailscale ping 100.x.x.x`
- Review LiteLLM logs on VPS B for model routing issues
