# Hybrid eBay/Vinted Listing Agent – Technical Specification

## 1. Overview

Design a self-hosted, Python-based AI agent system that helps users list items on eBay and Vinted by analyzing images, researching prices via scrapers, and generating optimized listings. The agent core is built with **LangChain** and **LangGraph** for orchestration, using **LiteLLM** as a hybrid gateway to route LLM calls to **OpenAI** (for high-quality reasoning) and **Ollama** (for cost-effective, private generation).[web:45][web:48]  
Scrapers for eBay (Apify actors) and Vinted (`vinted-scraper` or similar Python libraries) are exposed as tools, and the system integrates with **n8n** for UI and workflow triggering.[web:1][web:6][web:49]

Primary goals:

- Automate item identification and condition assessment from images.
- Fetch recent sold/comparable listings from eBay and Vinted for pricing.
- Recommend platform (eBay vs Vinted) based on prices and volume.
- Generate high-quality, SEO-optimized listing titles and descriptions.
- Operate within a self-hosted, privacy-respecting, extensible architecture.

---

## 2. System Architecture

### 2.1 Components

- **LiteLLM Gateway**
  - Acts as an OpenAI-compatible gateway.
  - Routes model calls to:
    - **OpenAI GPT-4 Turbo** (or similar) for complex reasoning.
    - **Ollama** models (e.g., `llama3`) for high-volume drafting.
  - Runs as its own service (container) and exposes an HTTP API (OpenAI-compatible) on a configurable port (e.g., `http://litellm:4000`).[web:45]

- **LangGraph Agent Service**
  - Python service (e.g., FastAPI) implementing:
    - LangChain for tooling and prompt logic.
    - LangGraph for agent orchestration and stateful workflows.[web:45][web:48]
  - Contains the “listing agent” graph that coordinates all steps.

- **Tool Layer (Scrapers & Utilities)**
  - **eBay sold listings scraper**:
    - Apify actors such as `caffein.dev/ebay-sold-listings` or similar completed sales APIs.[web:1][web:11][web:22]
  - **Vinted scraper**:
    - Python packages such as `vinted-scraper` or Apify Vinted Smart Scraper (`kazkn/vinted-smart-scraper`).[web:6][web:8][web:23]
  - Optional utilities:
    - Image captioning / tagging tool.
    - Metadata normalisation (brand, size, colour mapping).

- **Storage**
  - **Database**: Postgres (or similar) for:
    - Listings metadata.
    - Aggregated price statistics.
    - Audit logs and run history.
  - **Object Storage** (S3/MinIO/local FS) for:
    - Raw item images.
    - Optionally cached scraped responses.

- **Orchestration / UI Layer – n8n**
  - Workflow engine to:
    - Accept inputs (e.g., user uploading images).
    - Call the LangGraph Agent Service HTTP endpoints.
    - Route outputs to UI, notifications, or further automations.

### 2.2 Data Flow (High Level)

1. User (via n8n UI / front-end) uploads photos and optional metadata (brand, size, notes).
2. n8n calls LangGraph Agent Service `POST /listing` with files and metadata.
3. Service stores images and builds initial agent state.
4. LangGraph agent:
   - Infers item details and condition.
   - Calls eBay and Vinted tools to fetch comparable listings.
   - Aggregates prices and sales volume.
   - Decides recommended price and platform.
   - Generates final listing draft.
5. Service returns the final structured listing draft (and supporting stats) to n8n.
6. n8n stores results or presents them to the user, optionally triggering further automation.

---

## 3. Agent State and Data Model

### 3.1 Core Agent State (`ListState`)

Logical fields (type annotations are conceptual):

- `messages`: Conversation history for the agent (list of messages).
- `item_description`: Human-readable summary (e.g., “Sony WH-1000XM5 wireless headphones”).
- `item_type`: Category (e.g., “headphones”, “trainers”, “jacket”).
- `brand`: Brand string (e.g., “Sony”, “Nike”).
- `size`: Size string relevant to category (e.g., “UK 10”, “Large”).
- `color`: Main colour(s).
- `condition`: Enum:
  - `"New"`, `"Excellent"`, `"Good"`, `"Fair"`, `"Poor"`.
- `confidence`: Float 0–1 indicating certainty of item identification/condition.
- `photos`: List of URLs or file paths pointing to stored images.
- `ebay_price_stats`: Structured dict:
  - `num_listings`, `avg_price`, `median_price`, `min_price`, `max_price`, `items` (sample).
- `vinted_price_stats`: Same structure as `ebay_price_stats`.
- `suggested_price`: Recommended selling price.
- `preferred_platform`: Enum:
  - `"ebay"`, `"vinted"`, `"both"`.
- `listing_draft`: Struct:
  - `title`: Optimized title (≤ 80 characters for eBay).
  - `description`: Detailed, structured description (200–400 words).
  - `category_suggestions`: Optional category hints.
  - `shipping_suggestion`: Postage and service recommendations.
  - `returns_policy`: Short, clear returns summary.

### 3.2 Persistent Storage Schema (Conceptual)

- **Table: `listings`**
  - `id` (PK)
  - `created_at`, `updated_at`
  - `item_type`, `brand`, `size`, `color`
  - `condition`, `confidence`
  - `suggested_price`
  - `preferred_platform`
  - `title`, `description`
  - `raw_state` (JSONB snapshot of full `ListState`)

- **Table: `scrape_runs`**
  - `id` (PK)
  - `listing_id` (FK)
  - `source` (`"ebay"` or `"vinted"`)
  - `query_string`
  - `stats` (JSONB: price stats, volumes)
  - `raw_items` (optional JSONB, truncated sample)
  - `created_at`

---

## 4. LiteLLM Gateway Design

### 4.1 Purpose

- Provide a **single, OpenAI-compatible endpoint** for all LLM requests.
- Allow **hybrid routing**:
  - Complex reasoning → GPT-4 (OpenAI).
  - Long text generation → local Ollama models.

### 4.2 Logical Configuration

- Models registered in LiteLLM:
  - `openai:gpt-4-turbo` (or latest GPT-4.x reasoning model).
  - `ollama/llama3` (or chosen high-parameter local model).
- Routing strategy (conceptual):
  - Calls tagged as `reasoning` → GPT-4.
  - Calls tagged as `drafting` → Ollama.

### 4.3 Integration Contract

- LangChain will use **OpenAI-compatible clients** pointing at LiteLLM:
  - Base URL: `http://<litellm-host>:<port>/v1`.
  - API key: arbitrary or configured, depending on LiteLLM auth.

- Two logical LLM “instances” are defined in the agent service:
  - `reasoning_llm`: GPT-4 via LiteLLM.
  - `drafting_llm`: Ollama via LiteLLM.

---

## 5. Tools (Scraper & Utility Layer)

### 5.1 eBay Sold Listings Tool

- **Backend**: Apify actor such as:
  - `caffein.dev/ebay-sold-listings` or similar completed sales actors.[web:1][web:11][web:22]
- **Input Parameters**:
  - `query`: Search string, e.g., `"Sony WH-1000XM5 headphones used good condition"`.
  - Optional filters:
    - `country`: `"GB"` for eBay UK.
    - `maxResults` or equivalent (e.g., 50).
    - Date window (e.g., last 30–90 days), if supported by actor.
- **Output Schema** (normalized):
  - `num_listings`: int.
  - `avg_price`: float.
  - `median_price`: float.
  - `min_price`: float.
  - `max_price`: float.
  - `items`: List of up to N sample items, each with:
    - `title`, `price`, `currency`, `condition`, `sold_date`, `shipping_cost`, `url`.

### 5.2 Vinted Listings Tool

- **Backend**:
  - Python library `vinted-scraper` or Apify Vinted Smart Scraper (`kazkn/vinted-smart-scraper`).[web:6][web:8][web:23]
- **Input Parameters**:
  - `query`: String e.g., `"Nike Air Max 90 UK 10 used"`.
  - Location filter for UK buyers/sellers if supported.
  - `limit` (e.g., 30 results).
- **Output Schema**:
  - `num_listings`, `avg_price`, `median_price`, `min_price`, `max_price`.
  - `items`: Sample entries with `title`, `price`, `currency`, `condition`, `url`, `size`.

### 5.3 Image Analysis Utility (Optional Tool)

- **Purpose**:
  - Transform raw images into preliminary metadata:
    - Item type, brand (if visible), visible size, dominant colour, guessed condition, confidence score.
- **Backend Options**:
  - Local vision-capable model (e.g., via Ollama) or CLIP-based classifier.
- **Output**:
  - Structured metadata fed into initial state for `ListState`.

---

## 6. Agent Orchestration with LangGraph

### 6.1 Node Definitions

- **Node: `agent_reasoning`**
  - LLM: `reasoning_llm` (GPT-4 via LiteLLM).
  - Responsibilities:
    - Interpret initial description and image metadata.
    - Refine item type, brand, condition, size.
    - Decide whether confidence is sufficient or if clarification is needed.
    - Compose and trigger tool calls to:
      - `scrape_ebay_sold_listings`.
      - `scrape_vinted_listings`.

- **Node: `ebay_scrape` / `vinted_scrape`**
  - Implemented as LangChain tools integrated via LangGraph `ToolNode`.
  - Responsibilities:
    - Execute external HTTP or Python scrapers.
    - Normalize and store results in `ebay_price_stats` / `vinted_price_stats`.

- **Node: `agent_decision`**
  - LLM: `reasoning_llm`.
  - Responsibilities:
    - Read price statistics from both marketplaces.
    - Compute recommended `suggested_price`, using:
      - Median sold/comparable price minus a configurable discount (e.g., 10%) for faster sale.
    - Evaluate `preferred_platform`:
      - Consider volume (num_listings) and price level.
      - Rough rules of thumb:
        - eBay: tech/electronics, collectibles, structured categories.
        - Vinted: fashion, shoes, apparel.
    - Prepare a structured “decision summary” to feed into listing generation.

- **Node: `listing_writer`**
  - LLM: `drafting_llm` (Ollama via LiteLLM).
  - Responsibilities:
    - Generate:
      - Platform-appropriate title (80 chars max for eBay).
      - 200–400 word description with:
        - Key features and benefits.
        - Honest condition statement.
        - Sizing details.
        - Shipping and returns guidance.
      - Optional platform-specific variants (e.g., slightly different formats for Vinted vs eBay).
    - Return data in the `listing_draft` field.

- **Node: `clarify`**
  - LLM: `reasoning_llm`.
  - Trigger: If `confidence < threshold` (e.g., 0.7) or key fields (size, model) are missing.
  - Responsibilities:
    - Ask targeted, minimal questions (1–2) to the user, such as:
      - “Can you confirm the UK shoe size?”
      - “Is the box and manual included?”
    - Wait for response from caller (n8n / front-end) and feed it back into state.

- **Node: `END`**
  - Marks workflow completion with a fully-populated `listing_draft`.

### 6.2 Graph Structure (Conceptual)

1. **Entry** → `agent_reasoning`
2. From `agent_reasoning`:
   - If clarification needed → `clarify` → back to `agent_reasoning`.
   - Else → `ebay_scrape` and `vinted_scrape` (can be sequential or orchestrated).
3. After scrapers complete → `agent_decision`.
4. From `agent_decision` → `listing_writer`.
5. From `listing_writer` → `END`.

---

## 7. Workflow Logic and Behaviour

### 7.1 Standard Happy Path

1. User provides images and optional text describing the item.
2. Image analysis utility suggests:
   - “Item: Nike Air Max 90, Colour: White/Red, Condition: Good, Confidence: 0.83.”
3. `agent_reasoning`:
   - Confirms/adjusts these fields.
   - Builds query strings for eBay and Vinted.
4. `ebay_scrape` and `vinted_scrape`:
   - Fetch and aggregate sold/comparable listing data.
5. `agent_decision`:
   - Computes median prices and chooses a target price (e.g., median minus 10% for fast sale).
   - Chooses `preferred_platform` based on category and relative prices/volumes.
6. `listing_writer`:
   - Generates a final listing including title, description, suggested price and shipping.
7. Agent service responds to n8n with structured JSON.

### 7.2 Clarification Flow

- If:
  - Model cannot confidently recognise the exact model/size OR
  - Condition is ambiguous from photos,
- Then:
  - `agent_reasoning` sets a low confidence flag.
  - Transition to `clarify` node, which emits a concise user-facing question.
  - External UI (via n8n) collects the answer and re-invokes the graph with updated state.
  - Graph resumes from `agent_reasoning`.

---

## 8. API Contracts (Agent Service)

### 8.1 `POST /listing`

- **Purpose**: Start a listing-analysis-and-generation run for a single item.
- **Request**:
  - Content-Type: `multipart/form-data` or JSON plus separate image upload mechanism.
  - Fields:
    - `images[]`: One or more item photos.
    - `metadata` (JSON, optional):
      - `brand`, `size`, `color`, `notes`, etc.
- **Response** (JSON):
  - `listing_id`: Internal ID.
  - `listing_draft`:
    - `title`
    - `description`
    - `suggested_price`
    - `preferred_platform`
    - `ebay_price_stats`
    - `vinted_price_stats`
  - `clarification_required`: Boolean.
  - `clarification_question` (if applicable).

### 8.2 `POST /listing/{id}/clarify`

- **Purpose**: Provide user answers to clarification questions and resume the workflow.
- **Request** (JSON):
  - `answer`: Free text from user.
- **Response**:
  - Same structure as `POST /listing`, returning updated `listing_draft` and status flags.

### 8.3 `GET /listings/{id}`

- **Purpose**: Retrieve stored results for a given listing.
- **Response**:
  - Persisted `listing_draft` and any relevant run metadata.

---

## 9. Integration with n8n

### 9.1 n8n Workflow Outline

1. **Trigger**: UI or webhook with images/metadata.
2. **HTTP Node – “Create Listing”**:
   - Calls `POST /listing` on agent service.
3. **Conditional Node**:
   - If `clarification_required` is `true`:
     - Ask user via preferred channel (UI/form/WhatsApp agent).
     - Call `POST /listing/{id}/clarify` with user answer.
4. **Store / Display Result**:
   - Persist to DB or present the final draft in UI.
   - Optionally trigger other automations (e.g., Jira ticket, Slack message).

---

## 10. Deployment and Operations

### 10.1 Deployment Targets

- **Containers**:
  - `litellm` service.
  - `agent-service` (LangGraph + FastAPI).
  - `postgres` (or other DB).
  - `n8n`.
  - Optional `scraper-service` if not using SaaS scrapers.

### 10.2 Observability

- Log all:
  - Tool calls (including query and stats-only responses, no PII).
  - Node transitions and errors.
- Metrics:
  - Time per listing.
  - Tool error rates (eBay/Vinted scraping failures).
  - LLM costs/volume per model (via LiteLLM logs).

---

## 11. Non-Functional Requirements

- **Privacy**:
  - Avoid sending unnecessary PII to cloud LLMs; prefer Ollama for verbose content when privacy is critical.
- **Extensibility**:
  - Graph should support adding:
    - New marketplaces (Depop, Facebook Marketplace).
    - Additional tools (e.g., brand/size normalisation tables).
- **Resilience**:
  - If scrapers fail for one marketplace, still generate listing using available data and surface missing-data caveats.

---

## 12. Handover to Development

This specification is intended for:

- A development team to:
  - Implement the Python services (agent, tools, APIs).
  - Configure LiteLLM routing and Docker deployment.
  - Integrate with your existing n8n stack and infra.
- Or an AI agentic framework to:
  - Refine prompts and graph structure.
  - Generate concrete code implementations and CI/CD pipelines.

All implementation should adhere to this architecture while allowing iteration on model choices, prompts, and heuristic rules without breaking external API contracts.
