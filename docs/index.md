# Marketplace Listing Agent Documentation

Welcome to the documentation for the **Hybrid eBay/Vinted Listing Agent** - an AI-powered system for analyzing item photos, researching comparable prices, and generating optimized marketplace listings.

## Overview

The Marketplace Listing Agent is a self-hosted Python AI service that:

- **Analyzes item photos** using computer vision to identify items, brands, condition, and attributes
- **Researches market prices** on eBay and Vinted in real-time
- **Generates optimized listings** with titles, descriptions, and pricing recommendations
- **Supports both platforms** with platform-specific optimizations

## Quick Navigation

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | System architecture, components, and technical design |
| [Deployment Guide](deployment.md) | Step-by-step deployment instructions |
| [Agent Workflow](agent-workflow.md) | How the AI agent processes listings |
| [API Reference](api-reference.md) | Complete API endpoint documentation |
| [Configuration](configuration.md) | Environment variables and settings |
| [Development](development.md) | Setup for local development |
| [Troubleshooting](troubleshooting.md) | Common issues and solutions |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- API keys for:
  - OpenAI (for GPT-4o vision/reasoning)
  - Apify (for marketplace scraping)

### Deploy in 5 Minutes

```bash
# Clone the repository
git clone <repository-url>
cd marketplace-agent

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys

# Start all services
cd docker
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

## System Architecture

```
┌─────────────────┐
│   User/Client   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  FastAPI Service│────▶│   PostgreSQL    │
│   (Port 8000)   │     │   (Database)    │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  LangGraph Agent│────▶│  LiteLLM Gateway│
│   (7 Nodes)     │     │   (Port 4000)   │
└────────┬────────┘     └─────────────────┘
         │                        │
         │         ┌──────────────┴──────────────┐
         ▼         ▼                             ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ eBay Scraper    │  │ Vinted Scraper  │  │  Ollama (Local) │
│ (Apify)         │  │ (Apify/Custom)  │  │  (Llama 3)      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Core Features

### 1. Intelligent Image Analysis
- Multi-image support (up to 10 images per listing)
- Brand and model identification
- Condition assessment with confidence scoring
- Automatic accessory detection

### 2. Dual-Platform Price Research
- Real-time scraping of eBay sold listings
- Vinted marketplace price analysis
- Statistical price calculations (median, average, range)
- Platform recommendation based on market activity

### 3. AI-Powered Listing Generation
- Platform-optimized titles and descriptions
- SEO-friendly content
- Category suggestions
- Shipping and returns recommendations

### 4. Quality Assurance
- Confidence threshold validation
- User clarification loops
- Quality check with retry logic
- Human-in-the-loop for edge cases

## Technology Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI |
| Agent Orchestration | LangGraph |
| LLM Gateway | LiteLLM |
| Vision/Reasoning | GPT-4o (OpenAI) |
| Drafting | Llama 3 (Ollama) |
| Database | PostgreSQL 16 |
| Scraping | Apify |
| Workflow | n8n |
| Monitoring | Prometheus |

## License

MIT License - See the project repository for details.

## Support

For issues, questions, or contributions, please refer to:
- [Troubleshooting Guide](troubleshooting.md)
- GitHub Issues (if public repository)
- Project documentation
