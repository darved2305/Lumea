# Co-Code GGW Health Platform

A full-stack health companion platform for preventive health management. Upload medical reports, extract health metrics via OCR, track trends, and receive AI-powered health recommendations.

> ⚠️ **Disclaimer**: This platform is a support tool for personal health tracking. It does not provide medical advice, diagnosis, or treatment. Always consult a licensed healthcare professional for medical decisions.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Features](#features)
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

Co-Code GGW is a unified medical companion platform that enables users to:

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

### Health Profile
- Multi-step wizard with 6 steps (basics, measurements, conditions, medications, lifestyle, etc.)
- Tracks conditions, symptoms, medications, supplements, allergies
- Family medical history and genetic test results
- Completion score with missing field tracking

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

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) | `postgresql+asyncpg://user:pass@host:5432/db` |
| `JWT_SECRET` | Secret key for JWT signing | `your-secret-key-min-32-chars` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | `10080` (7 days) |
| `FRONTEND_ORIGIN` | CORS allowed origin | `http://localhost:5173` |
| `GROK_API_KEY` | xAI Grok API key (for AI summaries) | `gsk_...` |
| `GEMINI_API_KEY` | Google Gemini API key (optional fallback) | `AIza...` |
| `OLLAMA_BASE_URL` | Ollama server URL (optional) | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `medgemma:4b` |
| `USE_GEMINI_FALLBACK` | Enable Gemini fallback | `true` |

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
| `user_profiles` | Health profile data (basics, measurements, lifestyle) |
| `profile_conditions` | User medical conditions |
| `profile_medications` | Current medications |
| `profile_allergies` | Allergies and reactions |
| `profile_family_history` | Family medical history |
| `profile_recommendations` | Generated recommendations |
| `chat_sessions` | Assistant chat sessions |
| `chat_messages` | Chat message history |
| `report_ai_summaries` | Cached AI report summaries |
| `report_ai_comparisons` | Cached AI report comparisons |

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
    
    reports ||--o{ observations : extracts
    reports ||--o{ report_ai_summaries : summarized_by
    
    chat_sessions ||--o{ chat_messages : contains
```

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
