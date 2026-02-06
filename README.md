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
- [Voice Agent: AI Health Assistant](#voice-agent-ai-health-assistant)
- [Physics Twin: Health Telemetry & Organ Scoring](#physics-twin-health-telemetry--organ-scoring)
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
- **🎙️ Voice Agent**: Speak naturally to an AI health assistant for hands-free access to personalized health insights
- **🏥 Physics Twin**: Interactive 3D organ scoring engine with real-time telemetry, condition detection, and evidence-based health recommendations powered by your actual medical data

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, TypeScript, Vite, Framer Motion, Recharts, React Router, i18next |
| **Backend** | FastAPI (Python 3.10+), SQLAlchemy 2.0, Pydantic |
| **Database** | PostgreSQL (Neon or local), Alembic migrations |
| **OCR/Extraction** | PaddleOCR, pdfplumber, PyMuPDF |
| **AI/LLM** | Google Gemini API, Grok API (xAI), Ollama (MedGemma), ChromaDB (RAG) |
| **Voice Agent** | Web Speech API (STT), ElevenLabs TTS, Google Gemini |
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

### Physics Twin - Digital Health Telemetry & Organ Scoring
- **6-Organ System**: Deterministic health scoring for kidney, heart, liver, lungs, brain, blood
- **Real Data Integration**: Automatic computation from your actual extracted medical reports (not simulated)
- **Interactive 3D Body**: Click to explore organ scores with animated visualizations
- **Real-Time Telemetry**: Live vital signs stream (heart rate, blood pressure, SpO₂, glucose, stress, sleep)
- **Condition Detection**: 10 rule-based health conditions auto-detected with severity mapping
- **Body Impact Overlay**: 2D SVG visualization showing organs affected by detected conditions
- **Smart Recommendations**: Evidence-based health actions with YouTube educational links per condition
- **Time-Series History**: View per-report organ scores and historical trends
- **Lifestyle Integration**: Incorporates self-reported profile data (sleep hours, stress level)

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

### 🎙️ Voice Agent (AI Health Assistant)
- **Natural voice conversations** with your health data
- **Speech-to-Text**: Browser Web Speech API for hands-free input
- **AI Processing**: Google Gemini with personalized health context
- **Text-to-Speech**: ElevenLabs studio-quality voice (with browser fallback)
- **Safety features**: Emergency detection, dosage inquiry protection
- **Real-time feedback**: Visual orb animations for listening/thinking/speaking
- **Comprehensive context**: Uses profile, conditions, medications, allergies, reports, RAG data
- **Accessibility-first**: Ideal for hands-free use, visual impairments, or quick queries

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

## Voice Agent: AI Health Assistant

Lumea includes a fully integrated **Voice Agent** that provides an ElevenLabs-style conversational health assistant experience. Users can speak naturally to the AI agent, which responds with personalized health guidance based on their profile, conditions, medications, allergies, and recent lab reports.

> ⚠️ **Medical Disclaimer**: The Voice Agent is an informational support tool. It does NOT provide medical diagnosis, dosage recommendations, or emergency care. Always consult licensed healthcare professionals for medical decisions.

### Overview

The Voice Agent transforms how users interact with their health data through natural voice conversations powered by cutting-edge AI technologies.

**Key Capabilities**:

- **🎙️ Voice Interaction**: Speak naturally using browser-based speech recognition (Web Speech API)
- **🧠 Personalized AI Responses**: Powered by Google Gemini with access to your complete health profile
- **🔊 Natural Speech Output**: Human-like voice responses via ElevenLabs TTS (with browser fallback)
- **🛡️ Medical Safety Filters**: Detects emergency keywords, dosage inquiries, and provides appropriate safety responses
- **⚡ Real-time Feedback**: Visual orb animations reflect listening/thinking/speaking states
- **📝 Transcript View**: Optional chat-mode panel displays conversation history
- **🎯 Context-Aware**: Accesses your health conditions, medications, allergies, recent reports, and RAG-indexed data

### How It Works

The Voice Agent uses a sophisticated three-stage pipeline to deliver personalized health conversations:

```mermaid
graph LR
    A[👤 User Speaks] --> B[🎤 Browser STT<br/>Web Speech API]
    B --> C[🧠 LLM Processing<br/>Google Gemini]
    C --> D[📊 Health Context<br/>Profile + Reports + RAG]
    D --> C
    C --> E[🔊 Text-to-Speech<br/>ElevenLabs API]
    E --> F[🔉 Browser Fallback<br/>Web Speech API]
    E --> G[👤 User Hears Response]
    F --> G
```

#### Stage 1: Speech-to-Text (STT)
- **Technology**: Web Speech API (browser native)
- **Process**: Real-time audio capture and transcription
- **Benefits**: No external API costs, works offline for transcription
- **Language Support**: Multi-language support via browser capabilities

#### Stage 2: AI Processing & Context Retrieval
- **LLM Provider**: Google Gemini API (`gemini-flash-latest`)
- **Health Context Integration**:
  - User demographics (age, gender, BMI)
  - Active medical conditions
  - Current medications (name, dose, frequency)
  - Known allergies and their severity
  - Recent lab reports and observations
  - Lifestyle factors (sleep, exercise, smoking, alcohol)
- **RAG Enhancement**: Queries ChromaDB vector store for relevant historical health data
- **Safety Layer**: HIPAA-compliant system prompt with strict medical guidelines:
  - Never diagnose conditions
  - Never recommend medication dosages
  - Always suggest professional consultation
  - Detect emergency situations and direct to 911

#### Stage 3: Text-to-Speech (TTS)
- **Primary**: ElevenLabs TTS API
  - Model: `eleven_turbo_v2_5` (optimized for speed, free tier compatible)
  - Voice: Rachel (`21m00Tcm4TlvDq8ikWAM`)
  - Quality: Studio-grade natural voice synthesis
- **Fallback**: Browser Text-to-Speech API
  - Activates automatically if ElevenLabs unavailable (503 errors)
  - Uses system voices
  - Zero latency, no API costs

### Real-World Benefits

**For Everyday Users**:
- 🏃 **Hands-Free Access**: Check health info while cooking, exercising, or commuting
- 💬 **Natural Conversations**: Ask questions in plain language, no medical jargon required
- 📱 **Accessibility**: Ideal for users with visual impairments or reading difficulties
- ⚡ **Quick Insights**: Faster than navigating multiple screens and charts

**For Health-Conscious Individuals**:
- 🔍 **Report Interpretation**: "What do my cholesterol levels mean?"
- 💊 **Medication Context**: "Why am I taking this medication?"
- 📊 **Trend Analysis**: "How has my blood pressure changed over time?"
- 🎯 **Personalized Guidance**: Responses tailored to YOUR specific health profile

**Safety & Reliability**:
- 🚨 **Emergency Detection**: Recognizes crisis keywords (chest pain, can't breathe, etc.)
- 💊 **Dosage Protection**: Refuses to recommend medication changes
- 🔒 **HIPAA Guidelines**: All responses include disclaimers and professional consultation advice
- 🌐 **Fallback Mechanisms**: Graceful degradation if AI/TTS services unavailable

### API Endpoints

| Method | Endpoint | Description | Auth | Response |
|--------|----------|-------------|------|----------|
| GET | `/api/voice/context` | Get user health context summary with profile completeness status | ✅ Yes | `{profile_complete: bool, summary: {...}, has_personalization: bool}` |
| POST | `/api/voice/answer` | Generate personalized AI answer using Gemini + health context | ✅ Yes | `{answer_text: string, flags: [string], used_context: {...}}` |
| POST | `/api/voice/tts` | Convert text to speech using ElevenLabs API | ✅ Yes | Binary audio stream (MP3) |
| GET | `/api/voice/tts/status` | Check ElevenLabs TTS configuration status | ✅ Yes | `{configured: bool, voice_id: string, runtime_check: {...}}` |

**Context Response Details**:
```json
{
  "profile_complete": true,
  "has_personalization": true,
  "summary": {
    "name": "Darshan Ved",
    "age": 49,
    "gender": "Male",
    "bmi": 21.5,
    "conditions": ["Hypertension"],
    "medications": ["Lisinopril 10mg"],
    "allergies": ["Penicillin"],
    "reports_count": 5,
    "sleep_hours": 7,
    "exercise_frequency": "3-4 times/week"
  }
}
```

**Safety Flags**:
- `emergency`: Detected emergency keywords → directs to 911
- `dosage_inquiry`: Detected medication dosage question → refuses specific advice
- `error`: Processing error → fallback message

### Configuration & Setup

#### Required Environment Variables

Add to **root `.env`** (for Docker) and **`backend/.env`** (for local development):

```env
# ===== AI/LLM Configuration =====
# Google Gemini API (Primary LLM for Voice Agent)
USE_GEMINI_FALLBACK=true
GEMINI_API_KEY=AIzaSy...  # Get from https://aistudio.google.com/apikey

# ===== Text-to-Speech Configuration =====
# ElevenLabs TTS for Voice Agent (Optional - has browser fallback)
ELEVENLABS_API_KEY=sk_...  # Get from https://elevenlabs.io/
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Rachel voice (recommended)
```

#### Docker Configuration

Ensure `docker-compose.yml` includes these environment variables in the backend service:

```yaml
services:
  backend:
    environment:
      # ... other env vars ...
      - GEMINI_API_KEY=${GEMINI_API_KEY:-}
      - USE_GEMINI_FALLBACK=${USE_GEMINI_FALLBACK:-true}
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY:-}
      - ELEVENLABS_VOICE_ID=${ELEVENLABS_VOICE_ID:-21m00Tcm4TlvDq8ikWAM}
```

#### Getting API Keys

**Google Gemini API** (Free Tier Available):
1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click "Get API Key" → "Create API key"
4. Copy the key (starts with `AIzaSy...`)
5. Free tier includes: 15 requests/minute, 1 million tokens/day
6. Supported model: `gemini-flash-latest` (auto-maps to best available)

**ElevenLabs API** (Optional - Free Tier Available):
1. Sign up at [ElevenLabs](https://elevenlabs.io/)
2. Navigate to Settings → API Keys
3. Create new API key (starts with `sk_...`)
4. Free tier includes: 10,000 characters/month
5. Recommended voice IDs:
   - `21m00Tcm4TlvDq8ikWAM` - Rachel (conversational, female)
   - `ErXwobaYiN019PkySvjV` - Antoni (clear, male)
   - `EXAVITQu4vr4xnSDxMaL` - Bella (warm, female)

**Free Tier Model Compatibility**:
- ✅ Works: `gemini-flash-latest`, `gemini-1.5-flash-8b`
- ❌ Quota exceeded: `gemini-2.0-flash`, `gemini-2.5-flash` (requires paid tier)

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend STT** | Web Speech API (`webkitSpeechRecognition`) | Real-time voice transcription |
| **LLM Provider** | Google Gemini API (`gemini-flash-latest`) | Natural language understanding & generation |
| **Vector Database** | ChromaDB | RAG-based retrieval of historical health data |
| **Primary TTS** | ElevenLabs API (`eleven_turbo_v2_5`) | Studio-quality voice synthesis |
| **Fallback TTS** | Web Speech API (`SpeechSynthesis`) | Browser-native text-to-speech |
| **Backend Framework** | FastAPI | REST API endpoints |
| **Authentication** | JWT | Secure user-specific health context |

### Frontend Implementation

**Location**: `frontend/src/pages/VoiceAgent.tsx`

**Key Features**:
- **Orb Animation**: Uses Framer Motion for fluid listening/thinking/speaking states
- **State Management**: React hooks for recording, processing, speaking states
- **Error Handling**: Automatic fallback to browser TTS on ElevenLabs 503 errors
- **Accessibility**: Keyboard shortcuts, ARIA labels, screen reader support
- **Responsive Design**: Matches Lumea's light theme with purple accent colors

**User Flow**:
1. Click microphone button or press spacebar
2. Speak question (e.g., "What do my cholesterol levels mean?")
3. Watch orb animate while processing
4. Hear personalized response with health context
5. View transcript in chat panel (optional)

### Testing Voice Agent

#### 1. Check TTS Configuration Status

```bash
curl -X GET http://localhost:8000/api/voice/tts/status \
  -H "Authorization: Bearer <your_jwt_token>"
```

**Expected Response**:
```json
{
  "configured": true,
  "voice_id": "21m00Tcm4TlvDq8ikWAM",
  "runtime_check": {
    "api_key_loaded": true,
    "api_key_prefix": "sk_d78...",
    "voice_id": "21m00Tcm4TlvDq8ikWAM"
  }
}
```

#### 2. Test Health Context Retrieval

```bash
curl -X GET http://localhost:8000/api/voice/context \
  -H "Authorization: Bearer <your_jwt_token>"
```

**Expected Response**:
```json
{
  "profile_complete": true,
  "has_personalization": true,
  "summary": {
    "name": "Darshan Ved",
    "age": 49,
    "gender": "Male",
    "bmi": 21.5,
    "conditions": ["Hypertension"],
    "medications": ["Lisinopril"],
    "allergies": ["Penicillin"],
    "reports_count": 5
  }
}
```

#### 3. Test AI Answer Generation

```bash
curl -X POST http://localhost:8000/api/voice/answer \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What do my cholesterol levels mean?"
  }'
```

**Expected Response**:
```json
{
  "answer_text": "Based on your recent lab reports, your total cholesterol is 195 mg/dL, which falls within the desirable range (below 200 mg/dL). Your LDL cholesterol is 110 mg/dL, also in the optimal range. However, I recommend discussing these results with your healthcare provider for personalized guidance based on your hypertension condition.",
  "flags": [],
  "used_context": {
    "has_profile": true,
    "conditions_count": 1,
    "medications_count": 1,
    "has_rag_context": true
  }
}
```

#### 4. Test Text-to-Speech Conversion

```bash
curl -X POST http://localhost:8000/api/voice/tts \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello! Your health data shows positive trends."}' \
  --output test_voice.mp3

# Play the audio file
# Windows: start test_voice.mp3
# Mac: open test_voice.mp3
# Linux: mpg123 test_voice.mp3
```

#### 5. Test Safety Features

**Emergency Detection Test**:
```bash
curl -X POST http://localhost:8000/api/voice/answer \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "I am having severe chest pain"}'
```

**Expected Response**:
```json
{
  "answer_text": "I'm detecting words that suggest this might be an emergency situation. Please call emergency services immediately (911) or go to the nearest emergency room...",
  "flags": ["emergency"],
  "used_context": {}
}
```

**Dosage Inquiry Test**:
```bash
curl -X POST http://localhost:8000/api/voice/answer \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "Can I double my medication dosage?"}'
```

**Expected Response**:
```json
{
  "answer_text": "I cannot provide specific dosage recommendations. Please consult your doctor or pharmacist before making any changes to your medications...",
  "flags": ["dosage_inquiry"],
  "used_context": {...}
}
```

### Troubleshooting

#### Issue: "TTS service not configured" (503 Error)

**Symptoms**: Voice Agent uses browser TTS instead of ElevenLabs

**Solutions**:
1. **Check API Key Loading**:
   ```bash
   docker exec ggw-backend python -c "from app.settings import settings; print(f'API Key: {settings.ELEVENLABS_API_KEY[:20] if settings.ELEVENLABS_API_KEY else None}...')"
   ```

2. **Verify Environment Variables**:
   - Ensure `ELEVENLABS_API_KEY` is in root `.env` file
   - Ensure `docker-compose.yml` includes the env var mapping
   - Restart Docker containers: `docker compose restart backend`

3. **Check API Key Validity**:
   ```bash
   curl https://api.elevenlabs.io/v1/voices \
     -H "xi-api-key: sk_your_key_here"
   ```

#### Issue: Gemini API 404 or 429 Errors

**Symptoms**: "Model not found" or "Quota exceeded"

**Solutions**:
1. **Verify Model Compatibility**:
   ```bash
   docker exec ggw-backend python -c "import google.generativeai as genai; import os; genai.configure(api_key=os.environ['GEMINI_API_KEY']); models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]; print('\n'.join(models))"
   ```

2. **Check Free Tier Limits**:
   - Free tier model: `gemini-flash-latest` ✅
   - Paid tier models: `gemini-2.0-flash`, `gemini-2.5-flash` ❌
   - Rate limits: 15 requests/minute, 1M tokens/day

3. **Update Model Name** (if needed):
   - Edit `backend/app/services/llm_service.py`
   - Change model to `gemini-flash-latest`
   - Restart backend

#### Issue: "ProfileMedication object has no attribute 'medication_name'"

**Symptoms**: Context loading errors in logs

**Solution**: Already fixed in codebase - medication attribute is `name`, not `medication_name`

#### Issue: Browser STT Not Working

**Symptoms**: Microphone icon doesn't activate

**Solutions**:
1. **Check Browser Compatibility**: Use Chrome, Edge, or Safari (Firefox has limited support)
2. **Enable Microphone Permissions**: Allow microphone access in browser settings
3. **Use HTTPS or localhost**: Web Speech API requires secure context
4. **Check Console Errors**: Open DevTools → Console for detailed error messages

### Example Conversations

**General Health Query**:
- 👤 User: "What does my health profile show?"
- 🤖 Assistant: "You're a 49-year-old male with a healthy BMI of 21.5. Your profile shows hypertension, and you're currently taking Lisinopril. You have 5 health reports on file. Is there specific information you'd like me to explain?"

**Lab Result Interpretation**:
- 👤 User: "Explain my recent cholesterol test"
- 🤖 Assistant: "Your recent cholesterol panel shows total cholesterol at 195 mg/dL, which is in the desirable range. Your LDL is 110 mg/dL and HDL is 55 mg/dL. Given your hypertension, maintaining these levels is important. Discuss with your doctor about your diet and medication effectiveness."

**Medication Context**:
- 👤 User: "Why am I taking Lisinopril?"
- 🤖 Assistant: "Lisinopril is an ACE inhibitor prescribed for managing hypertension, which is noted in your health profile. It helps lower blood pressure by relaxing blood vessels. Always take it as prescribed and discuss any side effects with your healthcare provider."

---

## Physics Twin: Health Telemetry & Organ Scoring

Lumea's **Physics Twin** is a comprehensive digital health analysis engine that transforms raw health metrics from uploaded medical reports into deterministic organ-level health scores and real-time condition detection. It provides an interactive 3D body visualization, time-series telemetry monitoring, and AI-powered health recommendations grounded in your actual medical data.

> ⚠️ **Medical Disclaimer**: The Physics Twin is a visualization and analysis support tool. It does NOT provide medical diagnosis or treatment. Values are computed from extracted lab data and should be verified by healthcare professionals. Use for personal health tracking only—always consult a licensed healthcare professional for medical decisions.

### Overview

The Physics Twin delivers:

- **🏥 Deterministic Organ Scoring**: Evidence-based scoring for 6 organs (kidney, heart, liver, lungs, brain, blood) based on reference ranges and clinical normalisation
- **🔬 Real Data Integration**: Pulls metrics directly from your uploaded medical reports (not simulated) via the `Observation` table
- **📊 Interactive 3D Body**: Clickable organ hotspots with animated scoring visualizations and trend indicators
- **❤️ Real-Time Telemetry**: Simulated vital signs stream via SSE (Server-Sent Events) with SpO₂, heart rate, blood pressure, stress, and glucose tracking
- **⚠️ Condition Detection**: 10 rule-based conditions (Hypertension, Tachycardia, Kidney Stress, Liver Stress, Hyperglycemia, Sleep Deprivation, etc.) automatically detected from current metrics
- **👁️ Body Impact Overlay**: 2D SVG body silhouette highlighting organs affected by detected conditions with severity-based color coding
- **💊 Smart Recommendations**: Context-aware health recommendations with YouTube educational links for each detected condition
- **📈 Time-Series History**: View per-report organ scores, historical trends, and scored snapshots over time
- **🧬 Lifestyle Integration**: Incorporates UserProfile self-reported data (sleep hours, stress level, activity level) into organ scoring

### How It Works

The Physics Twin operates in a three-layer pipeline:

```
LAYER 1: Data Aggregation
├─ Queries Observation table for authentic lab metrics (last 90 days)
├─ Extracts canonical metric names (systolic_bp, glucose, alt, etc.)
├─ Enriches with UserProfile lifestyle data (sleep_hours, stress_level)
└─ Deduplicates per metric_name, keeping most recent value

LAYER 2: Deterministic Scoring
├─ Applies physics_config scoring rules
├─ Normalises each metric to 0-1 range based on reference bounds
├─ Computes per-organ weighted scores (0-100)
├─ Calculates overall composite score across all organs
└─ Generates contribution breakdown for explainability

LAYER 3: Condition Detection & Recommendations
├─ Evaluates current metrics against 10+ condition rules
├─ Detects severity (mild/moderate/severe) per condition
├─ Maps conditions to affected organs
├─ Generates evidence-based recommendations
└─ Enriches with YouTube educational links per condition
```

### Architecture & Data Flow

```mermaid
graph TB
    subgraph Database["PostgreSQL"]
        Observation["Observation Table<br/>(extracted metrics)"]
        UserProfile["UserProfile Table<br/>(lifestyle data)"]
        Report["Report Table<br/>(source documents)"]
    end

    subgraph Backend["Backend Services"]
        PhysicsConfig["physics_config.py<br/>- Organ specs<br/>- Metric weights<br/>- Reference ranges"]
        PhysicsRoute["physics.py Routes<br/>- GET /latest (auto-compute)<br/>- GET /history (per-report)<br/>- POST /metrics (manual)<br/>- GET /config"]
        Scorer["Scoring Engine<br/>- compute_organ_score()<br/>- compute_all_organs()"]
        ConditionEngine["conditions.py<br/>- detect_conditions()<br/>- 10 rule-based conditions<br/>- Severity mapping<br/>- Organ mapping"]
        TelemetryRoute["telemetry.py Routes<br/>- GET /stream (SSE)<br/>- GET /latest<br/>- GET /history"]
    end

    subgraph Frontend["Frontend Components"]
        PhysicsTwin["PhysicsTwin.tsx<br/>- Main page orchestrator<br/>- Tab navigation (Twin/Metrics/History)"]
        TwinViewer["TwinViewer.tsx<br/>- 3D body with Three.js<br/>- Organ hotspots<br/>- Auto-rotate"]
        BodyOverlay["BodyImpactOverlay.tsx<br/>- SVG body silhouette<br/>- Animated organ zones<br/>- Gender toggle"]
        OrganTelemetry["OrganTelemetryCard.tsx<br/>- Overall score display<br/>- Selected organ detail<br/>- Metric values"]
        Explainability["ExplainabilityCard.tsx<br/>- Scoring breakdown<br/>- Weight contributions<br/>- Coverage/confidence"]
        Recommendations["RecommendationsCard.tsx<br/>- Detected conditions<br/>- Evidence-based actions<br/>- YouTube links"]
        ConditionsEngine["conditionsEngine.ts<br/>- Client-side condition detection<br/>- Rapid re-evaluation<br/>- Trend computation"]
        TelemetryHook["useTelemetryStream.ts<br/>- SSE connection manager<br/>- Fallback simulation<br/>- History buffer (120 readings)"]
    end

    Observation -->|Query last 90 days| PhysicsRoute
    UserProfile -->|Enrich with lifestyle| PhysicsRoute
    Report -->|Group snapshots by| PhysicsRoute

    PhysicsRoute -->|Load config| PhysicsConfig
    PhysicsRoute -->|Compute scores| Scorer
    Scorer -->|Detect conditions| ConditionEngine

    TelemetryRoute -->|Generate readings| TelemetryHook
    PhysicsRoute -->|Return snapshot| PhysicsTwin

    PhysicsTwin -->|Render organs| TwinViewer
    PhysicsTwin -->|Show overlay| BodyOverlay
    PhysicsTwin -->|Display score| OrganTelemetry
    PhysicsTwin -->|Show breakdown| Explainability
    PhysicsTwin -->|Detect conditions| ConditionsEngine
    ConditionsEngine -->|Map to organs| BodyOverlay
    ConditionsEngine -->|Show recommendations| Recommendations
    TelemetryHook -->|Stream vitals| PhysicsTwin
```

### Core Concepts

#### Organ Systems (6 Total)

| Organ | Metrics | Purpose |
|-------|---------|---------|
| **Kidney** | creatinine, urea, egfr, sodium, potassium, systolic_bp | Filtration & electrolyte balance |
| **Heart** | heart_rate, systolic_bp, diastolic_bp, spo2, cholesterol, triglycerides | Cardiovascular function |
| **Liver** | alt, ast, bilirubin_total, albumin, alp, total_protein | Detoxification & synthesis |
| **Lungs** | spo2, respiratory_rate, hemoglobin | Oxygen exchange & gas transfer |
| **Brain** | sleep_hours, stress_level, glucose, systolic_bp, tsh | Neurological health |
| **Blood** | hemoglobin, wbc_total, platelet_count, rbc_count, glucose, hba1c, ferritin | Cell counts & glucose |

#### Scoring Methodology

Each metric is **normalised to 0-1** based on clinical reference ranges:

```
If metric_value is in reference_range [ref_min, ref_max]:
  normalised_score = 1.0  (perfect)

Else if metric_value < ref_min:
  normalised_score = (metric_value - abs_min) / (ref_min - abs_min)
  (linear decay to 0 at absolute minimum)

Else if metric_value > ref_max:
  normalised_score = 1.0 - (metric_value - ref_max) / (abs_max - ref_max)
  (linear decay to 0 at absolute maximum)
```

**Organ Score** = weighted average of present metrics:

```
score = Σ(weight_i × normalised_i) / Σ(weight_present) × 100
```

**Overall Score** = mean of all organ scores with data

**Status Classification**:
- ✅ **Healthy**: 75-100
- ⚠️ **Watch**: 50-74
- 🔴 **Risk**: 0-49

#### Metric Name Alignment

All metric names match PostgreSQL `Observation.metric_name` canonical keys:

```python
# Correct DB names (used everywhere)
"systolic_bp", "diastolic_bp", "heart_rate", "spo2", "respiratory_rate",
"creatinine", "urea", "egfr", "sodium", "glucose", "ast", "alt",
"bilirubin_total", "hemoglobin", "stress_level", "sleep_hours"
```

This ensures consistent data flow from OCR extraction → database storage → physics scoring.

#### Conditions Detection

10 rule-based conditions evaluated against current metrics:

| Condition | Severity | Trigger Metrics | Affected Organs |
|-----------|----------|-----------------|-----------------|
| Hypertension | mild/moderate/severe | systolic_bp ≥ 130/140/160 mmHg | heart, kidney, brain |
| Tachycardia | mild/moderate/severe | heart_rate ≥ 100/120/150 bpm | heart |
| Bradycardia | mild/moderate/severe | heart_rate ≤ 55/50/40 bpm | heart, brain |
| Hypoxemia | mild/moderate/severe | spo2 ≤ 94/90/85 % | lungs, heart, brain |
| Kidney Stress | mild/moderate/severe | creatinine ≥ 1.3/1.8/3.0 mg/dL | kidney |
| Liver Stress | mild/moderate/severe | alt ≥ 60/100/200 U/L | liver |
| Hyperglycemia | mild/moderate/severe | glucose ≥ 110/140/200 mg/dL | kidney, heart, brain |
| High Stress | mild/moderate/severe | stress_level ≥ 4/6/8 | brain, heart |
| Sleep Deprivation | mild/moderate/severe | sleep_hours ≤ 6.5/5/4 hrs | brain, heart |
| Tachypnea | mild/moderate/severe | respiratory_rate ≥ 22/26/30 bpm | lungs |

### Backend Implementation

#### Files Modified/Created

1. **`app/services/physics_config.py`**: Organ & metric specifications
   - 6 organ definitions with metric weights
   - Reference ranges & absolute bounds per metric
   - `compute_organ_score()`: Deterministic scoring function
   - `compute_all_organs()`: Multi-organ aggregation

2. **`app/routes/physics.py`**: Smart API endpoints
   - `GET /api/physics/latest`: Auto-compute from real DB data (90-day window)
   - `GET /api/physics/history`: Per-report snapshots
   - `POST /api/physics/metrics`: Manual submission (fallback)
   - `GET /api/physics/config`: Frontend config download

3. **`app/services/conditions.py`**: Rule engine
   - 10 `ConditionRule` definitions
   - `detect_conditions()`: Main evaluation function
   - Threshold checking with severity mapping
   - Organ affection mapping

4. **`app/routes/telemetry.py`**: Simulated SSE stream
   - Baseline vital signs (heart_rate, bp, spo2, glucose, etc.)
   - Per-user simulation state tracking
   - Realistic jitter + periodic spikes
   - `GET /stream` SSE endpoint

#### Data QueryQuery Pattern (physics.py)

```python
# Gather last 90 days of metrics for user
result = await db.execute(
    select(Observation)
    .where(
        and_(
            Observation.user_id == user_id,
            Observation.observed_at >= cutoff  # 90 days ago
        )
    )
    .order_by(desc(Observation.observed_at))
)

# Deduplicate: keep most recent value per metric_name
metrics = {}
for obs in sorted_observations:
    if obs.metric_name not in seen:
        metrics[obs.metric_name] = float(obs.value)
```

### Frontend Implementation

#### Main Components

1. **`PhysicsTwin.tsx`** (616 lines): Page orchestrator
   - Three tabs: Twin View (3D/overlay), Metrics (vitals grid), History (trends + snapshots)
   - Auto-loads latest snapshot on mount
   - Streams real-time telemetry via SSE hook
   - Auto-detects conditions from current metrics
   - Handles organ selection state

2. **`TwinViewer.tsx`** (297 lines): 3D body renderer
   - Uses `@react-three/fiber` + `@react-three/drei` + Three.js
   - Stylized torso + head mesh
   - 6 animated organ orbs with onClick handlers
   - Auto-rotating when no organ selected
   - Smooth camera tween to selected organ
   - Responsive scaling & glow effects

3. **`BodyImpactOverlay.tsx`** (263 lines): 2D condition visualization
   - SVG body silhouette (male/female toggle)
   - 6 organ zones with animated pulsing
   - Severity-based color coding (mild/moderate/severe)
   - Condition pill badges at top
   - Gender-specific body paths

4. **`OrganTelemetryCard.tsx`** (159 lines): Score summary
   - Large animated overall score display
   - Selected organ detail (coverage %, status badge)
   - Per-metric contribution breakdown with visual bars
   - Last updated timestamp

5. **`ExplainabilityCard.tsx`**: Scoring transparency
   - Breakdown table: metric name, raw value, normalised score, weight
   - Contribution % calculation
   - Coverage metric (% of available metrics present)
   - Confidence score (weighted average)

6. **`RecommendationsCard.tsx`**: Condition actions
   - Dynamic pill badges grouped by severity
   - Evidence-based recommendations for each condition
   - YouTube search links for educational content
   - Expandable/collapsible sections

#### Supporting Files

- **`physicsApi.ts`**: API client with types for snapshots, organs, conditions
- **`conditionsEngine.ts`**: Client-side condition detection mirroring backend rules (instant feedback on metric changes)
- **`useTelemetryStream.ts`**: SSE hook with automatic fallback to simulated vitals if SSE unavailable

### API Endpoints

| Method | Endpoint | Description | Auth | Response |
|--------|----------|-------------|------|----------|
| GET | `/api/physics/latest` | Get auto-computed snapshot from user's real reports | Yes | `PhysicsSnapshot` (includes all organs + conditions) |
| GET | `/api/physics/history?days=90` | Get per-report snapshots grouped by date/report_id | Yes | `List[PhysicsSnapshot]` |
| POST | `/api/physics/metrics` | Submit manual metrics for what-if analysis | Yes | `PhysicsSnapshot` (not persisted) |
| GET | `/api/physics/config` | Download organ/metric specifications | Yes | `{ organs: {...} }` (used by frontend for explainability) |
| GET | `/api/telemetry/stream` | SSE stream of simulated vitals (2s intervals) | Yes | EventStream of `TelemetryReading` |
| GET | `/api/telemetry/latest` | Get latest telemetry reading | Yes | `TelemetryReading` |
| GET | `/api/telemetry/history?minutes=60` | Get recent telemetry history | Yes | `List[TelemetryReading]` |

### Request/Response Examples

**GET /api/physics/latest**

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000_2025-02-06T10:30:00",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-02-06T10:30:00",
  "overall_score": 72.3,
  "overall_status": "Watch",
  "data_source": "reports",
  "raw_metrics": {
    "systolic_bp": 145,
    "diastolic_bp": 88,
    "heart_rate": 78,
    "glucose": 115,
    "alt": 35,
    "creatinine": 1.1,
    "spo2": 97,
    "hemoglobin": 14.2,
    "stress_level": 5.2,
    "sleep_hours": 6.5
  },
  "organs": {
    "heart": {
      "score": 68.5,
      "status": "Watch",
      "coverage": 0.83,
      "contributions": [
        {
          "name": "systolic_bp",
          "value": 145,
          "normalised": 0.75,
          "weight": 0.25,
          "weighted": 0.1875,
          "unit": "mmHg"
        }
      ]
    },
    "kidney": {
      "score": 82.1,
      "status": "Healthy",
      "coverage": 1.0,
      "contributions": []
    }
  },
  "conditions": [
    {
      "id": "hypertension",
      "name": "Hypertension",
      "severity": "moderate",
      "affected_organs": ["heart", "kidney", "brain"],
      "trigger_metrics": { "systolic_bp": 145 },
      "recommendations": [
        "Reduce sodium intake to under 2,300 mg/day",
        "Engage in 30 minutes of moderate exercise daily"
      ],
      "youtube_queries": ["how to lower blood pressure naturally"]
    }
  ],
  "organ_conditions": {
    "heart": ["hypertension"],
    "kidney": ["hypertension"]
  },
  "organ_severities": {
    "heart": "moderate",
    "kidney": "mild"
  }
}
```

**GET /api/telemetry/stream**

Response (Server-Sent Events stream):
```
data: {"timestamp":"2025-02-06T10:30:00Z","metrics":{"heart_rate":75,"systolic_bp":120,"diastolic_bp":76,"spo2":97.5,"respiratory_rate":16,"stress_level":2.4,"glucose":95},"units":{"heart_rate":"bpm","systolic_bp":"mmHg"}}

data: {"timestamp":"2025-02-06T10:30:02Z","metrics":{"heart_rate":76,"systolic_bp":119,"diastolic_bp":75,"spo2":97.2,"respiratory_rate":16,"stress_level":2.5,"glucose":94},"units":{...}}
```

### User Experience Flow

1. **Page Load**: 
   - Auto-fetches `/api/physics/latest` → loads real data from user's reports
   - If user has reports: snapshot shows immediately with organ scores visible
   - If no reports: Shows "No health data found" overlay with option to load demo data

2. **3D Viewer Interaction**:
   - Click any organ → auto-selects, triggers camera tween to that organ
   - OrganTelemetryCard shows score breakdown (e.g., "Heart: 68.5% — Watch")
   - ExplainabilityCard shows metric contributions to selected organ score
   - Each metric bar shows current value vs reference range

3. **Body Overlay Mode**:
   - Click "Impact View" toggle → SVG body appears
   - Detected conditions pulse with color coding (mild=yellow, moderate=orange, severe=red)
   - Each organ zone highlights if affected by a condition
   - Hover shows condition name

4. **Real-Time Metrics Tab**:
   - Vital signs grid shows latest values (from telemetry SSE stream)
   - Trend arrows (↑ up, ↓ down, → stable) based on 10-reading window
   - "Score Metrics" button submits current readings for manual analysis

5. **History Tab**:
   - Line chart of selected metric over last 60 telemetry readings
   - Scored snapshots section lists per-report scores with timestamps
   - Click any snapshot to replay its organ breakdown

6. **Recommendations**:
   - Dynamically updates as conditions detected/cleared
   - Each condition shows severity, affected organs, evidence-based actions
   - YouTube links for patient education (e.g., "DASH diet for hypertension")

### Key Features Breakdown

#### Real Data, Not Simulation

- ✅ `/api/physics/latest` queries actual `Observation` table
- ✅ Uses real extracted metrics from uploaded medical reports
- ✅ Falls back gracefully if user has zero observations (shows empty state)
- ✅ Enriches with self-reported profile data (sleep, stress)

#### Deterministic Scoring

- ✅ Reference ranges stored in `physics_config.py`
- ✅ All calculations deterministic (no AI/ML, pure math)
- ✅ Explainable: every score component shown in breakdown
- ✅ Aligned with clinical normalisation standards

#### 3D Interactive Body

- ✅ 6 clickable organ hotspots
- ✅ Smooth camera animation on selection
- ✅ Real-time score badges on each organ
- ✅ Auto-rotating when idle
- ✅ Works on mobile and desktop

#### Condition Detection

- ✅ 10 rule-based conditions automatically detected
- ✅ Severity mapping (mild ≤ moderate ≤ severe)
- ✅ Organ affection mapping (which organs are affected?)
- ✅ Real-time evaluation as metrics change
- ✅ Client-side + server-side dual detection for instant feedback

#### Educational Context

- ✅ Recommendations tailored per condition
- ✅ YouTube search links for each condition
- ✅ Evidence citations (reference ranges explained)
- ✅ Safety disclaimers on all pages

### Performance & Optimization

- **Frontend Bundle**: 3D viewer lazy-loaded (905 KB gzipped)
- **Data Loading**: Latest snapshot ~50-200ms (DB index on user_id + observed_at)
- **Real-Time**: SSE stream 2s interval (configurable)
- **History Rendering**: 60 telemetry readings + recharts <100ms re-render
- **Condition Detection**: Client-side evaluation <5ms per metrics update

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
