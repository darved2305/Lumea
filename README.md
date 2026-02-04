# Lumea Health Platform

A full-stack health companion platform for preventive health management. Upload medical reports, extract health metrics via OCR, track trends, and receive AI-powered health recommendations.

> ⚠️ **Disclaimer**: This platform is a support tool for personal health tracking. It does not provide medical advice, diagnosis, or treatment. Always consult a licensed healthcare professional for medical decisions.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Features](#features)
- [Medicines: Find Cheap Alternatives](#medicines-find-cheap-alternatives)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Database](#database)
- [API Reference](#api-reference)
- [WebSocket Events](#websocket-events)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Lumea is a unified medical companion platform that enables users to:

- **Upload medical reports** (PDF, images) and automatically extract health metrics via OCR
- **Track health profiles** with comprehensive intake forms (conditions, medications, allergies, family history)
- **Monitor health trends** with a computed Health Index and interactive charts
- **Receive AI recommendations** based on extracted lab values and health patterns
- **Compare reports over time** with AI-powered summaries and trend analysis
- **Chat with an AI assistant** grounded in your personal health data

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, TypeScript, Vite, Framer Motion, Recharts, React Router, i18next |
| **Backend** | FastAPI (Python 3.10+), SQLAlchemy 2.0, Pydantic |
| **Database** | PostgreSQL (Neon or local), Alembic migrations |
| **OCR/Extraction** | PaddleOCR, pdfplumber, PyMuPDF |
| **AI/LLM** | Grok API (xAI), Ollama (MedGemma), Gemini fallback, ChromaDB (RAG) |
| **Realtime** | WebSocket (FastAPI native) |
| **Auth** | JWT (python-jose), bcrypt |

---

## Architecture

```mermaid
flowchart TB
    subgraph Client["Frontend (React)"]
        UI[React UI]
        WS[WebSocket Client]
    end

    subgraph API["Backend (FastAPI)"]
        Auth[Auth Routes]
        Dashboard[Dashboard Routes]
        Reports[Reports Routes]
        Profile[Profile Routes]
        Recommendations[Recommendations Routes]
        AISummary[AI Summary Routes]
        Assistant[Assistant Routes]
        WSServer[WebSocket Server]
    end

    subgraph Services["Backend Services"]
        OCR[PDF/OCR Extractor]
        Classifier[Document Classifier]
        MetricExtractor[Metric Extractor]
        MetricsService[Metrics Service]
        RecommendationEngine[Recommendation Engine]
        AISummaryService[AI Summary Service]
        RAG[RAG Service]
        LLM[LLM Service]
    end

    subgraph External["External Services"]
        GrokAPI[Grok API]
        Ollama[Ollama / MedGemma]
        Gemini[Gemini API]
    end

    subgraph Storage["Data Layer"]
        DB[(PostgreSQL / Neon)]
        ChromaDB[(ChromaDB Vector Store)]
        FileStorage[File Storage]
    end

    UI --> Auth
    UI --> Dashboard
    UI --> Reports
    UI --> Profile
    UI --> Recommendations
    UI --> AISummary
    UI --> Assistant
    WS <--> WSServer

    Reports --> OCR
    OCR --> Classifier
    Classifier --> MetricExtractor
    MetricExtractor --> MetricsService
    MetricsService --> RecommendationEngine

    AISummary --> AISummaryService
    AISummaryService --> GrokAPI
    Assistant --> RAG
    RAG --> ChromaDB
    RAG --> LLM
    LLM --> Ollama
    LLM --> Gemini

    Auth --> DB
    Dashboard --> DB
    Reports --> DB
    Reports --> FileStorage
    Profile --> DB
    Recommendations --> DB
    AISummary --> DB
```

### Data Flow: Report Upload to Health Index

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant OCR
    participant Classifier
    participant Extractor
    participant DB
    participant WebSocket

    User->>Frontend: Upload PDF/Image
    Frontend->>Backend: POST /api/reports/upload
    Backend->>DB: Create report (status: uploaded)
    Backend-->>Frontend: {id, status: uploaded}
    
    Backend->>OCR: Extract text (background)
    OCR-->>Backend: Raw text
    Backend->>Classifier: Classify document
    Classifier-->>Backend: Category + doc_type
    Backend->>Extractor: Extract metrics
    Extractor-->>Backend: Observations[]
    Backend->>DB: Save observations + update report
    Backend->>DB: Recompute health index
    Backend->>WebSocket: emit report_parsed
    WebSocket-->>Frontend: report_parsed event
    Frontend->>Frontend: Refresh UI
```

---

## Features

### Document Upload & OCR
- Supported formats: PDF, PNG, JPG, JPEG, TIFF
- Max file size: 50MB
- Automatic text extraction (text-first, OCR fallback)
- Document classification: Lab, Dental, MRI, X-ray, Prescription, Sleep

### Health Profile & Reminders
- Multi-step wizard with 6 steps (basics, measurements, conditions, medications, lifestyle, etc.)
- Tracks conditions, symptoms, medications, supplements, allergies
- Family medical history and genetic test results
- **Once completed, users are never re-asked** – profile status persists in DB
- "Profile Complete ✅" indicator with quick-edit access via Settings page
- **Real-time SMS reminders** via Twilio (or mock mode for testing)
- Background scheduler processes due reminders every 60 seconds
- Default reminders auto-generated: medication, appointment, checkup, hydration

### Health Index & Trends
- Computed health index (0-100) based on lab values
- Factor contributions breakdown (glucose, lipids, vitamins, etc.)
- Time-series trends (1D, 1W, 1M views)
- Abnormal value flagging with reference ranges

### AI Recommendations
- Rule-based engine analyzing lab values vs reference ranges
- Severity levels: INFO, WARNING, URGENT
- Categories: lifestyle, screening, follow-up, urgent
- Evidence-based with citations

### AI Report Summary
- Single report AI summary with key findings
- Multi-report comparison (2-6 reports, same type)
- Highlights: positive, needs attention, next steps
- Cached results with hash-based invalidation

### Health Assistant
- RAG-powered chat grounded in user's health data
- Citations from reports and observations
- WebSocket streaming for real-time responses

---

## Medicines: Find Cheap Alternatives

Lumea includes a comprehensive medicine management system that helps users find affordable generic alternatives to prescribed medicines and locate nearby pharmacies, including government-sponsored Jan Aushadhi Kendras offering subsidized medications.

> ⚠️ **Medical Disclaimer**: This feature is a support tool for informational purposes only. It does NOT provide medical advice. Always consult your doctor or pharmacist before switching medicines or starting new treatments.

### Overview

The Medicines feature enables users to:

- **Search for medicines** by brand name or free-text queries
- **Upload prescriptions** and automatically extract medicines via OCR/AI
- **Find affordable alternatives** with ranked matching by clinical equivalence
- **Compare prices** including Jan Aushadhi (government-fixed price) options
- **Locate nearby pharmacies** including generic and Jan Aushadhi pharmacies
- **Track medications** with personal notes and dosage schedules

### User Flow

1. **Input Medicine Information**
   - User enters brand name (e.g., "Aspirin 500mg") or uploads prescription image
   - System extracts text via OCR or Grok AI parsing

2. **Normalize Medicine Data**
   - `MedicineNormalizer` service extracts: salt, strength, form (tablet/capsule/liquid), release type (immediate/sustained)
   - Queries `GenericCatalog` table to validate and standardize extraction

3. **Find Substitutes**
   - `SubstituteFinder` queries database for alternatives with 4-tier ranked matching:
     - **Tier 1** (1.0 score): Exact match on salt + strength + form + release type
     - **Tier 2** (0.8 score): Same salt + strength + form
     - **Tier 3** (0.6 score): Same salt + strength
     - **Tier 4** (0.4 score): Same salt only
   - Results sorted by price (Jan Aushadhi first for lowest cost)

4. **Locate Pharmacies** (Optional)
   - User enters location (latitude/longitude) and search radius
   - `PharmacyLocator` queries Google Places API for pharmacies
   - Results include Jan Aushadhi Kendras (government pharmacies) and private pharmacies
   - Results cached for 1 hour to reduce API calls

5. **Save & Track**
   - User can save medicines to personal list with notes
   - Each save creates `UserSavedMedicine` entry for quick reference

### Architecture Diagram

```mermaid
flowchart TB
    subgraph Frontend["Frontend (React)"]
        MedicinesPage["Medicines.tsx Page"]
        SubstitutePanel["Substitute Finder Panel"]
        PharmacyPanel["Pharmacy Locator Panel"]
    end

    subgraph API["Backend API (FastAPI)"]
        NormalizeRoute["POST /normalize<br/>POST /normalize/batch"]
        SubstituteRoute["POST /substitutes<br/>POST /substitutes/from-text"]
        PharmacyRoute["GET /pharmacies/nearby<br/>GET /pharmacies/{id}<br/>POST /pharmacies/{id}/click"]
        SavedRoute["POST /saved<br/>GET /saved<br/>DELETE /saved/{id}"]
    end

    subgraph Services["Backend Services"]
        MedicineNormalizer["MedicineNormalizer<br/>- normalize()<br/>- normalize_batch()"]
        SubstituteFinder["SubstituteFinder<br/>- find_substitutes()<br/>- save_medicine()"]
        PharmacyLocator["PharmacyLocator<br/>- search_nearby()<br/>- get_place_details()<br/>- 1hr cache"]
        GrokService["GrokMedicineService<br/>- get_alternatives_for_text()"]
    end

    subgraph External["External Services"]
        GooglePlaces["Google Places API<br/>(Pharmacy Search)"]
        GrokAPI["Grok xAI API<br/>(Medicine Parsing)"]
    end

    subgraph Storage["Data Layer"]
        DB[(PostgreSQL)]
        GenericCatalog["GenericCatalog Table<br/>(600K+ medicines)"]
        UserSavedMedicine["UserSavedMedicine Table"]
        SubstituteQuery["SubstituteQuery Table<br/>(Analytics)"]
        PharmacyClick["PharmacyClick Table<br/>(Analytics)"]
    end

    MedicinesPage --> SubstitutePanel
    MedicinesPage --> PharmacyPanel
    SubstitutePanel --> SubstituteRoute
    PharmacyPanel --> PharmacyRoute
    PharmacyPanel --> SavedRoute

    SubstituteRoute --> GrokService
    SubstituteRoute --> MedicineNormalizer
    SubstituteRoute --> SubstituteFinder
    PharmacyRoute --> PharmacyLocator

    MedicineNormalizer --> DB
    MedicineNormalizer --> GenericCatalog
    SubstituteFinder --> DB
    SubstituteFinder --> GenericCatalog
    SubstituteFinder --> SubstituteQuery
    PharmacyLocator --> GooglePlaces
    PharmacyLocator --> PharmacyClick

    GrokService --> GrokAPI
    GrokAPI -->|Parsed results| SubstituteFinder
```

### API Endpoints

| Method | Endpoint | Description | Auth | Key Parameters |
|--------|----------|-------------|------|-----------------|
| POST | `/api/medicines/normalize` | Normalize single medicine text | Yes | `text: str` → Returns `NormalizedMedicine` |
| POST | `/api/medicines/normalize/batch` | Normalize multiple medicines (prescription lines) | Yes | `texts: List[str]` → Returns `List[NormalizedMedicine]` |
| POST | `/api/medicines/substitutes` | Find substitutes from structured data | Yes | `salt, strength, form, release_type` → Returns ranked substitutes |
| POST | `/api/medicines/substitutes/from-text` | Find substitutes from free-form text (AI-powered) | Yes | `text: str` → Grok AI parsing → Returns alternatives with prices |
| GET | `/api/medicines/pharmacies/nearby` | Search nearby pharmacies by location | Yes | `lat, lng, radius_m=1000, type=all, page_token` → Returns paginated pharmacies |
| GET | `/api/medicines/pharmacies/{place_id}` | Get pharmacy details | Yes | `place_id: str` → Returns address, phone, hours, rating |
| POST | `/api/medicines/pharmacies/{place_id}/click` | Log pharmacy interaction (analytics) | Yes | `action: directions\|call\|website` |
| POST | `/api/medicines/saved` | Save medicine to user list | Yes | `brand_name, salt, strength, form, notes` |
| GET | `/api/medicines/saved` | Get user's saved medicines | Yes | Returns list of `UserSavedMedicine` |
| DELETE | `/api/medicines/saved/{medicine_id}` | Delete saved medicine | Yes | `medicine_id: UUID` |

### Request/Response Examples

**POST /api/medicines/substitutes/from-text**

Request:
```json
{
  "text": "Aspirin 500mg tablets"
}
```

Response:
```json
{
  "original_text": "Aspirin 500mg tablets",
  "normalized": {
    "brand_name": "Aspirin",
    "salt": "Acetylsalicylic Acid",
    "strength": "500",
    "form": "tablet",
    "release_type": "immediate",
    "confidence": 0.95
  },
  "substitutes": [
    {
      "rank": 1,
      "product_name": "Jan Aushadhi Aspirin 500mg",
      "salt": "Acetylsalicylic Acid",
      "strength": "500",
      "form": "tablet",
      "mrp": "5.00",
      "is_jan_aushadhi": true,
      "match_score": 1.0,
      "match_reason": "Exact match: Same salt, strength, form, and type"
    },
    {
      "rank": 2,
      "product_name": "Ecosprin 500mg",
      "salt": "Acetylsalicylic Acid",
      "strength": "500",
      "form": "tablet",
      "mrp": "8.50",
      "is_jan_aushadhi": false,
      "match_score": 1.0,
      "match_reason": "Exact match: Same salt, strength, form, and type"
    }
  ],
  "disclaimer": "Always confirm with your doctor or pharmacist before switching medicines"
}
```

**GET /api/medicines/pharmacies/nearby**

Request:
```
GET /api/medicines/pharmacies/nearby?lat=40.7128&lng=-74.0060&radius_m=1000&type=all
```

Response:
```json
{
  "pharmacies": [
    {
      "place_id": "ChIJN1blbgBQwokRzKgy6E_B_1Q",
      "name": "Jan Aushadhi Kendra - Downtown",
      "address": "123 Main St, New York, NY 10001",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "rating": 4.7,
      "is_open": true,
      "is_jan_aushadhi": true,
      "phone": "+1-212-555-0123"
    },
    {
      "place_id": "ChIJrc_p_1BQwokRzKgy6E_B_2Q",
      "name": "Metro Pharmacy",
      "address": "456 Broadway, New York, NY 10002",
      "latitude": 40.7150,
      "longitude": -74.0030,
      "rating": 4.2,
      "is_open": true,
      "is_jan_aushadhi": false,
      "phone": "+1-212-555-0456"
    }
  ],
  "next_page_token": null,
  "total_results": 2
}
```

---

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.10+
- PostgreSQL 14+ (or Neon cloud database)
- (Optional) Ollama for local LLM

### 1. Clone the Repository

```bash
git clone https://github.com/darved2305/Co-Code-2.0-ggw.git
cd Co-Code-2.0-ggw
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate
# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL, JWT_SECRET, GROK_API_KEY

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Access the Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Docker Setup (Alternative)

```bash
# From project root
docker-compose up --build
```

Services:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- PostgreSQL: localhost:5432

---

## Environment Variables

Create a `.env` file in the `backend/` directory:

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) | `postgresql+asyncpg://user:pass@host:5432/db` | Yes |
| `JWT_SECRET` | Secret key for JWT signing | `your-secret-key-min-32-chars` | Yes |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` | No (default: HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | `10080` (7 days) | No (default: 10080) |
| `FRONTEND_ORIGIN` | CORS allowed origin | `http://localhost:5173` | Yes |
| `GROK_API_KEY` | xAI Grok API key (for AI summaries & medicine parsing) | `gsk_...` | Yes |
| `XAI_API_BASE` | xAI API endpoint base URL | `https://api.x.ai/v1` | No (default provided) |
| `GROK_MODEL` | Grok model identifier | `grok-beta` | No (default: grok-beta) |
| `GOOGLE_PLACES_API_KEY` | Google Maps API key (for pharmacy search) | `AIzaSyD...` | No (fallback to mock data) |
| `GEMINI_API_KEY` | Google Gemini API key (optional fallback for summaries) | `AIza...` | No |
| `OLLAMA_BASE_URL` | Ollama server URL (optional) | `http://localhost:11434` | No |
| `OLLAMA_MODEL` | Ollama model name | `medgemma:4b` | No |
| `USE_GEMINI_FALLBACK` | Enable Gemini fallback when Grok unavailable | `true` | No (default: false) |
| `SMS_MODE` | SMS sending mode: `twilio` (real) or `mock` (test/log only) | `mock` | No (default: mock) |
| `SMS_TEST_TO_NUMBER` | Default phone for test SMS (mock mode) | `+15551234567` | No |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID (required for `twilio` mode) | `ACxxxxxxxx` | No* |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token (required for `twilio` mode) | `xxxxxxxxx` | No* |
| `TWILIO_FROM_NUMBER` | Twilio phone number (required for `twilio` mode) | `+15559876543` | No* |
| `REMINDER_SCHEDULER_ENABLED` | Enable/disable background reminder scheduler | `true` | No (default: true) |
| `REMINDER_CHECK_INTERVAL_SECONDS` | How often scheduler checks for due reminders | `60` | No (default: 60) |

**Medicines Feature Notes:**

- **GROK_API_KEY**: Required for free-text medicine parsing (e.g., "Aspirin 500mg tablets" → structured data)
- **GOOGLE_PLACES_API_KEY**: Optional for pharmacy search. If not set, returns mock pharmacy data for testing
- **XAI_API_BASE** & **GROK_MODEL**: Typically use defaults; modify only for different xAI endpoints or model versions

**SMS Reminders Feature Notes:**

- **SMS_MODE**: Set to `mock` for development/testing (logs to console), `twilio` for production
- **TWILIO_***: Required only when `SMS_MODE=twilio`. Get credentials from [Twilio Console](https://console.twilio.com/)
- **REMINDER_SCHEDULER_ENABLED**: Scheduler runs in-process with APScheduler; disable during tests if needed

See [backend/.env.example](backend/.env.example) for a complete template.

---

## Database

### Migrations

Migrations are managed with Alembic:

```bash
cd backend

# Apply all migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Check current revision
alembic current
```

### Core Tables

| Table | Description |
|-------|-------------|
| `users` | User accounts (email, password_hash, onboarding status) |
| `login_events` | Login audit trail |
| `reports` | Uploaded documents (file path, OCR text, classification) |
| `observations` | Extracted health metrics (value, unit, reference range, flag) |
| `health_metrics` | Computed scores (health_index, contributions) |
| `user_profiles` | Health profile data (basics, measurements, lifestyle, is_completed, phone_number) |
| `profile_conditions` | User medical conditions |
| `profile_medications` | Current medications |
| `profile_allergies` | Allergies and reactions |
| `profile_family_history` | Family medical history |
| `profile_recommendations` | Generated recommendations |
| `reminders` | User health reminders (medication, appointment, checkup, hydration) |
| `reminder_events` | SMS send audit log (status, error messages, timestamps) |
| `chat_sessions` | Assistant chat sessions |
| `chat_messages` | Chat message history |
| `report_ai_summaries` | Cached AI report summaries |
| `report_ai_comparisons` | Cached AI report comparisons |
| `generic_catalog` | Medicine database (600K+ products, indexed by salt/product_name) |
| `user_saved_medicines` | User's saved medicines (brand name, dosage, notes) |
| `substitute_queries` | Analytics: medicine searches and results |
| `pharmacy_clicks` | Analytics: pharmacy interaction tracking (directions, calls, website) |
| `user_location_consent` | Location permissions for pharmacy search |

### Entity Relationships

```mermaid
erDiagram
    users ||--o{ reports : uploads
    users ||--o{ observations : has
    users ||--o{ health_metrics : has
    users ||--o| user_profiles : has
    users ||--o{ profile_conditions : has
    users ||--o{ profile_medications : takes
    users ||--o{ profile_allergies : has
    users ||--o{ chat_sessions : owns
    users ||--o{ report_ai_summaries : generates
    users ||--o{ report_ai_comparisons : generates
    users ||--o{ user_saved_medicines : saves
    users ||--o{ substitute_queries : searches
    users ||--o{ pharmacy_clicks : clicks
    users ||--o| user_location_consent : grants
    
    user_profiles ||--o{ reminders : has
    reminders ||--o{ reminder_events : logs
    
    reports ||--o{ observations : extracts
    reports ||--o{ report_ai_summaries : summarized_by
    
    chat_sessions ||--o{ chat_messages : contains
    
    user_saved_medicines ||--o{ generic_catalog : references
    substitute_queries ||--o{ generic_catalog : queries
```

### Medicines Database Schema

**generic_catalog** - Seeded from PMBI (Pharmaceutical Market Bureau of India) data

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `product_name` | VARCHAR | Brand/product name (indexed) |
| `salt` | VARCHAR | Active pharmaceutical ingredient (indexed) |
| `strength` | VARCHAR | e.g., "500mg", "100mcg" |
| `form` | VARCHAR | e.g., "tablet", "capsule", "liquid", "injection" |
| `release_type` | VARCHAR | e.g., "immediate", "sustained" |
| `mrp` | DECIMAL | Maximum retail price |
| `manufacturer` | VARCHAR | Manufacturing company |
| `source` | VARCHAR | Data source (e.g., "jan_aushadhi", "pmbi") |
| `is_jan_aushadhi` | BOOLEAN | Government-fixed price indicator |
| `created_at` | TIMESTAMP | Record creation time |

**user_saved_medicines** - User's tracked medicines

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Foreign key → users |
| `original_name` | VARCHAR | User-entered medicine name |
| `salt` | VARCHAR | Normalized salt |
| `strength` | VARCHAR | Normalized strength |
| `form` | VARCHAR | Normalized form |
| `release_type` | VARCHAR | Normalized release type |
| `schedule_json` | JSONB | Optional: dosage schedule (morning, noon, evening) |
| `notes` | TEXT | User's personal notes |
| `created_at` | TIMESTAMP | When medicine was saved |

**substitute_queries** - Analytics table

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Foreign key → users |
| `query_raw` | VARCHAR | Original user input |
| `normalized_json` | JSONB | Extracted fields (salt, strength, form, release_type) |
| `results_json` | JSONB | Array of matching substitutes |
| `results_count` | INTEGER | Number of alternatives found |
| `created_at` | TIMESTAMP | Query timestamp |

**pharmacy_clicks** - Analytics table

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Foreign key → users |
| `place_id` | VARCHAR | Google Places API place ID |
| `place_name` | VARCHAR | Pharmacy name |
| `mode` | VARCHAR | Action: "directions", "call", "website" |
| `created_at` | TIMESTAMP | Click timestamp |

**user_location_consent** - Privacy tracking

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Foreign key → users (unique) |
| `consent` | BOOLEAN | Location permission granted/revoked |
| `updated_at` | TIMESTAMP | Last update |

---

## API Reference

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/register` | Create new account | No |
| POST | `/api/auth/login` | Login, get JWT | No |
| POST | `/api/auth/logout` | Logout, clear cookie | Yes |

### Dashboard

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/me/bootstrap` | Get user state after login | Yes |
| GET | `/api/dashboard/summary` | Health index with factor breakdown | Yes |
| GET | `/api/dashboard/trends` | Time-series data for metrics | Yes |

### Reports

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/reports` | List user's reports | Yes |
| POST | `/api/reports/upload` | Upload new report | Yes |
| GET | `/api/reports/{id}` | Get report details | Yes |
| POST | `/api/reports/{id}/confirm` | Confirm extracted values | Yes |
| DELETE | `/api/reports/{id}` | Delete report | Yes |
| GET | `/api/reports/{id}/debug` | Debug extraction info | Yes |

### Profile

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/profile` | Get full profile | Yes |
| PUT | `/api/profile` | Update profile | Yes |
| POST | `/api/profile/conditions` | Add conditions | Yes |
| POST | `/api/profile/medications` | Add medications | Yes |
| POST | `/api/profile/allergies` | Add allergies | Yes |
| POST | `/api/profile/recompute` | Trigger recomputation | Yes |

### Profile/Me (Simplified)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/profile/me` | Get current user's profile with completion status | Yes |
| PUT | `/api/profile/me` | Create or update profile (upsert) | Yes |
| PATCH | `/api/profile/me` | Partial profile update | Yes |

### Reminders

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/reminders` | List all reminders for user | Yes |
| POST | `/api/reminders` | Create new reminder | Yes |
| PATCH | `/api/reminders/{id}` | Update reminder | Yes |
| DELETE | `/api/reminders/{id}` | Delete reminder | Yes |
| POST | `/api/reminders/generate-default` | Generate default reminders | Yes |

### SMS (Testing)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/sms/test` | Send test SMS (mock or real based on SMS_MODE) | Yes |

### Recommendations

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/recommendations` | Get recommendations | Yes |
| GET | `/api/recommendations/summary` | Get summary counts | Yes |
| POST | `/api/recommendations/regenerate` | Force regeneration | Yes |

### AI Summary

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/ai/reports-for-summary` | List reports for selection | Yes |
| GET | `/api/ai/reports/{id}/file` | Get report file | Yes |
| POST | `/api/ai/report-summary` | Generate single report summary | Yes |
| POST | `/api/ai/report-compare` | Compare multiple reports | Yes |
| POST | `/api/ai/validate-comparison` | Validate selection | Yes |
| GET | `/api/ai/categories` | Get distinct categories | Yes |

### Assistant

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/assistant/chat` | Chat with AI assistant | Yes |

### Example Request/Response

**POST /api/auth/login**

Request:
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "created_at": "2026-01-15T10:30:00Z"
  }
}
```

**POST /api/ai/report-summary**

Request:
```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440001",
  "force_regenerate": false
}
```

Response:
```json
{
  "summary_json": {
    "title": "Blood Panel Analysis - January 2026",
    "highlights": {
      "positive": ["Hemoglobin within normal range", "Glucose levels stable"],
      "needs_attention": ["LDL cholesterol slightly elevated"],
      "next_steps": ["Consider dietary changes", "Retest in 3 months"]
    },
    "plain_language_summary": "Your blood panel shows mostly healthy values...",
    "key_findings": [
      {"item": "LDL Cholesterol", "evidence": "142 mg/dL (ref: <100)"}
    ],
    "confidence": 0.85
  },
  "cached": false,
  "generated_at": "2026-02-02T10:30:00Z",
  "model_name": "grok-beta"
}
```

---

## WebSocket Events

Connect: `ws://localhost:8000/ws?token=<jwt_token>`

### Events Sent to Client

| Event | Payload | Description |
|-------|---------|-------------|
| `connected` | `{message, user_id}` | Connection established |
| `pong` | `{timestamp}` | Response to ping |
| `report_processing_started` | `{report_id, progress}` | OCR processing began |
| `report_parsed` | `{report_id, extracted_metrics_count, status}` | OCR completed |
| `health_index_updated` | `{score, breakdown, confidence, updated_at}` | Health index recalculated |
| `trends_updated` | `{metrics: [...]}` | Trend data changed |
| `reports_list_updated` | `{}` | Reports list changed |
| `recommendations_updated` | `{count, urgent_count}` | Recommendations regenerated |
| `profile_updated` | `{updated_at}` | Profile changed |
| `chat_token` | `{token}` | Streaming chat token |
| `chat_complete` | `{full_response, citations, session_id}` | Chat response complete |

### Events Received from Client

| Event | Payload | Description |
|-------|---------|-------------|
| `ping` | `{}` | Keepalive ping |
| `subscribe` | `{topics: [...]}` | Subscribe to topics |
| `chat_request` | `{message, session_id}` | Start streaming chat |

---

## Testing

### Run Tests

```bash
cd backend

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_routes_auth.py
```

### Test Files

- `test_routes_auth.py` - Authentication endpoints
- `test_routes_dashboard.py` - Dashboard endpoints
- `test_routes_reports.py` - Report upload/management
- `test_routes_recommendations.py` - Recommendation endpoints
- `test_lab_parser.py` - Lab value extraction
- `test_pdf_extractor.py` - PDF/OCR extraction
- `test_metrics_service.py` - Health index computation
- `test_websocket_manager.py` - WebSocket connection management

### Manual QA Checklist

1. ☐ Register a new account
2. ☐ Login and verify dashboard loads
3. ☐ Upload a PDF lab report
4. ☐ Verify OCR extraction completes (WebSocket notification)
5. ☐ Check extracted metrics appear in reports list
6. ☐ Verify health index updates on dashboard
7. ☐ Complete health profile wizard
8. ☐ Check recommendations generate
9. ☐ Open AI Summary page, select a report
10. ☐ Generate AI summary, verify it displays
11. ☐ Select 2 reports of same type, generate comparison
12. ☐ Try selecting mixed types, verify warning appears
13. ☐ Test Medicines feature: search for a medicine (e.g., "Aspirin 500mg")
14. ☐ Verify substitutes appear with prices and Jan Aushadhi options highlighted
15. ☐ Test pharmacy search by entering your location
16. ☐ Verify nearby pharmacies appear with ratings and distance
17. ☐ Try filtering pharmacies by type (all/jan_aushadhi/generic)
18. ☐ Save a medicine and verify it appears in saved list

### Medicines Feature Testing

```bash
cd backend

# Test medicines normalization
pytest tests/test_medicines_normalizer.py

# Test substitute finder
pytest tests/test_medicines_substitutes.py

# Test pharmacy locator
pytest tests/test_medicines_pharmacy_locator.py

# Test medicines routes
pytest tests/test_routes_medicines.py
```

### Medicines Manual Testing

1. **Test Medicine Normalization**
   ```bash
   curl -X POST http://localhost:8000/api/medicines/normalize \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"text": "Aspirin 500mg tablet"}'
   ```
   Expected: `NormalizedMedicine` with extracted salt, strength, form

2. **Test Substitute Search (AI-Powered)**
   ```bash
   curl -X POST http://localhost:8000/api/medicines/substitutes/from-text \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"text": "Crocin 650mg for fever"}'
   ```
   Expected: Ranked list of alternatives with prices

3. **Test Pharmacy Search**
   ```bash
   curl -X GET "http://localhost:8000/api/medicines/pharmacies/nearby?lat=40.7128&lng=-74.0060&radius_m=1000&type=all" \
     -H "Authorization: Bearer <token>"
   ```
   Expected: List of nearby pharmacies with ratings

4. **Test Save Medicine**
   ```bash
   curl -X POST http://localhost:8000/api/medicines/saved \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "brand_name": "Aspirin",
       "salt": "Acetylsalicylic Acid",
       "strength": "500",
       "form": "tablet",
       "release_type": "immediate",
       "notes": "Take with food"
     }'
   ```
   Expected: `UserSavedMedicine` object saved to database

### Medicines Troubleshooting

**Problem: "No alternatives found" when searching for a medicine**

- **Cause**: Medicine not in `generic_catalog` table
- **Solution**: 
  - Verify PMBI/Jan Aushadhi seed data was loaded during migration
  - Check database: `SELECT COUNT(*) FROM generic_catalog;` should show 600K+ records
  - Try searching by generic name instead of brand name (e.g., "Acetylsalicylic Acid" instead of "Aspirin")
  - Check logs for Grok API errors if using free-text search

**Problem: "Google Places API 401" or pharmacy search returns empty**

- **Cause**: `GOOGLE_PLACES_API_KEY` not set or API quota exceeded
- **Solution**:
  - Verify `GOOGLE_PLACES_API_KEY` is set in `.env`: `echo $GOOGLE_PLACES_API_KEY`
  - Check Google Cloud Console for API key validity and quota limits
  - If quota exceeded, wait 24 hours or upgrade billing
  - During development, feature falls back to mock pharmacy data when API key is missing
  - Mock data is useful for frontend testing without API costs

**Problem: Slow medicine normalization or substitute search**

- **Cause**: Missing database indexes on high-cardinality columns
- **Solution**:
  - Verify indexes exist on `generic_catalog`: `SELECT indexname FROM pg_indexes WHERE tablename='generic_catalog';`
  - Should see indexes on: `product_name`, `salt`, `user_id`
  - If missing, run: `alembic upgrade head` to apply latest migrations
  - Check database query performance: Enable `EXPLAIN ANALYZE` in PostgreSQL
  - Profile with: `SELECT pg_size_pretty(pg_total_relation_size('generic_catalog'));`

**Problem: Grok API errors when parsing prescription images**

- **Cause**: Invalid image format, API key expired, or API rate limit
- **Solution**:
  - Verify image is clear and readable (JPG, PNG, TIFF)
  - Test API key directly: `curl -H "Authorization: Bearer $GROK_API_KEY" https://api.x.ai/v1/models`
  - Check Grok API status at https://status.x.ai
  - Review backend logs: `docker logs <backend-container>` or `tail uvicorn.log`
  - If rate-limited, implement request throttling in `medicine_normalizer.py`

**Problem: Pharmacy search cache not updating**

- **Cause**: In-memory cache TTL (1 hour) not expired
- **Solution**:
  - Manually clear cache by restarting backend service
  - Cache is per-search key (lat/lng/radius): different locations create new cache entries
  - Check cache size in logs: Search for "pharmacy_cache" debug messages
  - To disable caching for testing, set `PharmacyLocator.CACHE_TTL_SECONDS = 0`

**Problem: User saved medicines not persisting**

- **Cause**: Database migration not applied or user_id foreign key constraint
- **Solution**:
  - Verify `user_saved_medicines` table exists: `\dt user_saved_medicines` in psql
  - Run migrations: `cd backend && alembic upgrade head`
  - Verify user exists and authenticated: Check JWT token contains valid `sub` (user_id)
  - Check database logs for constraint errors: `docker logs <postgres-container>`
---

## Deployment

### Docker Compose (Development/Staging)

```bash
docker-compose up -d
```

Includes:
- PostgreSQL 16 (Alpine)
- FastAPI backend with hot reload
- Vite React frontend with hot reload

### Production Considerations

1. **Database**: Use Neon, Supabase, or managed PostgreSQL
2. **Backend**: Deploy to Railway, Render, or AWS ECS
3. **Frontend**: Deploy to Vercel, Netlify, or Cloudflare Pages
4. **Secrets**: Use environment variables, never commit `.env`
5. **HTTPS**: Enable secure cookies in production
6. **CORS**: Update `FRONTEND_ORIGIN` for production domain

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and test
4. Commit with clear messages: `git commit -m "Add: feature description"`
5. Push and create a Pull Request

### Code Style

- Backend: Follow PEP 8, use type hints
- Frontend: Follow ESLint/Prettier config
- Commits: Use conventional commit format

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Support

For issues or questions, open a GitHub issue or contact the maintainers.
