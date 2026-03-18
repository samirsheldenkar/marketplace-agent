# API Reference

Complete reference for the Marketplace Listing Agent REST API.

## Base URL

```
Local Development: http://localhost:8000/api/v1
Production: https://api.yourdomain.com/api/v1
```

## Authentication

All API endpoints (except `/health`) require authentication via Bearer token:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/listing
```

**Error Response (401 Unauthorized)**:
```json
{
  "detail": "Invalid or missing API key"
}
```

## Endpoints

### Health Check

Check the health status of the API and its dependencies.

```http
GET /health
```

**Authentication**: None

**Response** (200 OK):
```json
{
  "status": "healthy",
  "services": {
    "database": {
      "status": "healthy"
    },
    "litellm": {
      "status": "healthy"
    }
  },
  "version": "0.1.0"
}
```

**Response** (200 OK - degraded):
```json
{
  "status": "degraded",
  "services": {
    "database": {
      "status": "healthy"
    },
    "litellm": {
      "status": "unhealthy",
      "error": "Connection timeout"
    }
  },
  "version": "0.1.0"
}
```

---

### Create Listing

Create a new listing by uploading item photos. The agent will analyze the images, research prices, and generate a complete listing draft.

```http
POST /listing
```

**Content-Type**: `multipart/form-data`

**Authentication**: Required

#### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `images` | File[] | Yes | 1-10 image files (jpg, png, webp, gif) |
| `brand` | string | No | Known brand hint |
| `size` | string | No | Size information |
| `color` | string | No | Color hint |
| `notes` | string | No | Additional condition notes |
| `fast_sale` | boolean | No | Apply discount for quick sale (default: true) |

#### Request Example

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "images=@photo3.jpg" \
  -F "brand=Sony" \
  -F "notes=Minor scratches on case" \
  -F "fast_sale=true" \
  http://localhost:8000/api/v1/listing
```

#### Success Response (200 OK)

```json
{
  "listing_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "item": {
    "type": "headphones",
    "brand": "Sony",
    "model": "WH-1000XM5",
    "condition": "Good",
    "confidence": 0.92
  },
  "pricing": {
    "suggested_price": 189.00,
    "currency": "GBP",
    "preferred_platform": "ebay",
    "platform_reasoning": "Higher listing volume on eBay (45 vs 12 listings)",
    "ebay_stats": {
      "num_listings": 45,
      "avg_price": 235.50,
      "median_price": 220.00,
      "min_price": 180.00,
      "max_price": 299.99,
      "items": [...]
    },
    "vinted_stats": {
      "num_listings": 12,
      "avg_price": 210.00,
      "median_price": 200.00,
      "min_price": 175.00,
      "max_price": 250.00,
      "items": [...]
    }
  },
  "listing_draft": {
    "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones - Black",
    "description": "Selling my excellent condition Sony WH-1000XM5 wireless headphones. These industry-leading noise cancelling headphones feature...",
    "category_suggestions": [
      "Consumer Electronics > Headphones",
      "Sound & Vision > Headphones"
    ],
    "shipping_suggestion": "Royal Mail Tracked 48",
    "returns_policy": "30-day returns accepted, buyer pays return shipping"
  }
}
```

#### Clarification Response (202 Accepted)

When the agent needs more information:

```json
{
  "listing_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "clarification",
  "clarification_question": "I can see this is an electronic device, but I'm having trouble identifying the specific item. Could you tell me: 1) What type of item is this (e.g., headphones, speaker, camera)? 2) What brand is it, if visible?",
  "item": {
    "type": "electronics",
    "brand": null,
    "model": null,
    "condition": "unknown",
    "confidence": 0.45
  },
  "pricing": null,
  "listing_draft": null
}
```

#### Error Responses

**400 Bad Request - Invalid Input**:
```json
{
  "detail": "Maximum 10 images allowed"
}
```

**400 Bad Request - Invalid Image**:
```json
{
  "detail": "Invalid image format. Allowed: jpg, jpeg, png, webp, gif"
}
```

**503 Service Unavailable - LLM Error**:
```json
{
  "detail": "LLM gateway unavailable"
}
```

**503 Service Unavailable - Scraper Error**:
```json
{
  "detail": "Marketplace scrapers unavailable"
}
```

---

### Submit Clarification

Submit an answer to a clarification question for a listing awaiting clarification.

```http
POST /listing/{listing_id}/clarify
```

**Content-Type**: `application/json`

**Authentication**: Required

#### Path Parameters

| Field | Type | Description |
|-------|------|-------------|
| `listing_id` | UUID | The listing ID from the clarification response |

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `answer` | string | Yes | User's answer to the clarification question |

#### Request Example

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"answer": "It\'s a vintage Leica M6 camera from 1984"}' \
  http://localhost:8000/api/v1/listing/550e8400-e29b-41d4-a716-446655440000/clarify
```

#### Success Response (200 OK)

Returns the completed listing (same format as Create Listing success response).

#### Clarification Response (200 OK - Still Needs Clarification)

```json
{
  "listing_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "clarification",
  "clarification_question": "Thank you! Could you also tell me the condition? Does it have any scratches, dents, or functional issues?",
  "item": {
    "type": "camera",
    "brand": "Leica",
    "model": "M6",
    "condition": "unknown",
    "confidence": 0.65
  },
  "pricing": null,
  "listing_draft": null
}
```

#### Error Responses

**404 Not Found**:
```json
{
  "detail": "Listing 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

**400 Bad Request - Wrong Status**:
```json
{
  "detail": "Listing is not awaiting clarification (status: completed)"
}
```

---

### Get Listing

Retrieve a listing by ID.

```http
GET /listing/{listing_id}
```

**Authentication**: Required

#### Path Parameters

| Field | Type | Description |
|-------|------|-------------|
| `listing_id` | UUID | The listing ID |

#### Request Example

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/listing/550e8400-e29b-41d4-a716-446655440000
```

#### Success Response (200 OK)

```json
{
  "listing_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "item": {
    "type": "headphones",
    "brand": "Sony",
    "model": "WH-1000XM5",
    "condition": "Good",
    "confidence": 0.92
  },
  "pricing": {
    "suggested_price": 189.00,
    "currency": "GBP",
    "preferred_platform": "ebay",
    "platform_reasoning": "Higher listing volume on eBay (45 vs 12 listings)"
  },
  "listing_draft": {
    "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones - Black",
    "description": "Selling my excellent condition Sony WH-1000XM5 wireless headphones...",
    "category_suggestions": [
      "Consumer Electronics > Headphones"
    ],
    "shipping_suggestion": "Royal Mail Tracked 48",
    "returns_policy": "30-day returns accepted"
  }
}
```

#### Error Responses

**404 Not Found**:
```json
{
  "detail": "Listing 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

### Metrics

Retrieve Prometheus metrics for monitoring.

```http
GET /metrics
```

**Authentication**: None

#### Response

Returns Prometheus metrics in text format:

```
# HELP marketplace_listing_creation_duration_seconds Listing creation duration
# TYPE marketplace_listing_creation_duration_seconds histogram
marketplace_listing_creation_duration_seconds_bucket{le="10.0"} 5
marketplace_listing_creation_duration_seconds_bucket{le="30.0"} 12
marketplace_listing_creation_duration_seconds_bucket{le="60.0"} 15

# HELP marketplace_listing_status_total Total listings by status
# TYPE marketplace_listing_status_total counter
marketplace_listing_status_total{status="completed"} 42
marketplace_listing_status_total{status="clarification"} 8
marketplace_listing_status_total{status="failed"} 2
```

---

## Data Models

### ItemInfo

```typescript
interface ItemInfo {
  type: string;          // Item category
  brand: string | null;  // Brand name
  model: string | null;  // Model identifier
  condition: string;     // New | Excellent | Good | Fair | Poor
  confidence: number;    // 0.0 - 1.0
}
```

### PricingInfo

```typescript
interface PricingInfo {
  suggested_price: number;
  currency: string;              // "GBP"
  preferred_platform: string;    // "ebay" | "vinted" | "both"
  platform_reasoning: string;
  ebay_stats?: PriceStats;
  vinted_stats?: PriceStats;
}
```

### PriceStats

```typescript
interface PriceStats {
  num_listings: number;
  avg_price: number;
  median_price: number;
  min_price: number;
  max_price: number;
  items: SoldItem[];
}

interface SoldItem {
  title: string;
  price: number;
  sold_date: string;
  url?: string;
}
```

### ListingDraft

```typescript
interface ListingDraft {
  title: string;
  description: string;
  category_suggestions: string[];
  shipping_suggestion: string;
  returns_policy: string;
}
```

### ListingStatus

Possible status values:

| Status | Description |
|--------|-------------|
| `pending` | Listing created, waiting for processing |
| `processing` | Agent is actively processing the listing |
| `completed` | Listing successfully generated |
| `clarification` | Waiting for user clarification |
| `failed` | Processing failed |

---

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Default limit**: 30 requests per minute per API key
- **Burst allowance**: 5 requests
- **Headers returned**:
  - `X-RateLimit-Limit`: 30
  - `X-RateLimit-Remaining`: 27
  - `X-RateLimit-Reset`: 1643723400

**Rate Limit Response (429 Too Many Requests)**:
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

Configure rate limiting via environment variables:
```bash
MARKETPLACE_API_RATE_LIMIT_RPM=60  # Increase to 60 RPM
MARKETPLACE_REDIS_URL=redis://localhost:6379  # Enable Redis-backed rate limiting
```

---

## Error Codes

| HTTP Code | Meaning | Common Causes |
|-----------|---------|---------------|
| 200 | OK | Successful request |
| 202 | Accepted | Clarification needed |
| 400 | Bad Request | Invalid input, validation error |
| 401 | Unauthorized | Missing or invalid API key |
| 404 | Not Found | Listing doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | LLM or scraper unavailable |

---

## SDK Examples

### Python

```python
import requests

API_KEY = "your-api-key"
BASE_URL = "http://localhost:8000/api/v1"

headers = {"Authorization": f"Bearer {API_KEY}"}

# Create listing
with open("item.jpg", "rb") as f:
    files = [("images", ("item.jpg", f, "image/jpeg"))]
    data = {"brand": "Nike", "fast_sale": "true"}
    
    response = requests.post(
        f"{BASE_URL}/listing",
        headers=headers,
        files=files,
        data=data
    )
    
    result = response.json()
    print(f"Listing ID: {result['listing_id']}")
    print(f"Suggested Price: £{result['pricing']['suggested_price']}")
```

### JavaScript/Node.js

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

const API_KEY = 'your-api-key';
const BASE_URL = 'http://localhost:8000/api/v1';

async function createListing() {
  const form = new FormData();
  form.append('images', fs.createReadStream('item.jpg'));
  form.append('brand', 'Nike');
  form.append('fast_sale', 'true');
  
  const response = await axios.post(`${BASE_URL}/listing`, form, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      ...form.getHeaders()
    }
  });
  
  console.log('Listing ID:', response.data.listing_id);
  console.log('Suggested Price: £', response.data.pricing.suggested_price);
}
```

### cURL

```bash
# Create listing
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "images=@item1.jpg" \
  -F "images=@item2.jpg" \
  -F "brand=Apple" \
  -F "fast_sale=true" \
  http://localhost:8000/api/v1/listing

# Get listing
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/listing/550e8400-e29b-41d4-a716-446655440000

# Submit clarification
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"answer": "It is an iPhone 13 Pro in Sierra Blue"}' \
  http://localhost:8000/api/v1/listing/550e8400-e29b-41d4-a716-446655440000/clarify
```
