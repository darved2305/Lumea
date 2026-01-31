# Co-Code GGW - Unified Medical Companion Platform

A comprehensive full-stack health companion platform built with modern technologies to enable preventive health management, intelligent health reminders, and real-time health insights through AI-powered analysis.

![Status](https://img.shields.io/badge/status-active-success)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![React](https://img.shields.io/badge/React-18.0+-61dafb)

---

## 🎯 Overview

Co-Code GGW is a production-ready health technology platform designed to bridge the gap between users and personalized preventive healthcare. The platform combines artificial intelligence, secure data management, and real-time analytics to provide actionable health insights.

**Key Objectives:**
- Empower users with data-driven health insights
- Automate health management through intelligent reminders
- Provide AI-powered health guidance and recommendations
- Enable seamless health data extraction from lab reports
- Maintain enterprise-grade security and data privacy

---

## ✨ Core Features

### 🔐 Authentication & User Management
- **Multi-factor security** with JWT-based authentication
- **Role-based access control** (RBAC) for differentiated access levels
- **Secure password storage** using bcrypt hashing
- **Session management** with automatic token refresh
- **Email verification** for account security
- Support for both guest and authenticated users

### 👤 Health Profile Management
- **Comprehensive health intake forms** with multi-step validation
- **Real-time calculations** for BMI and health metrics
- **Medical condition tracking** with severity levels
- **Medication & allergy documentation** with interaction warnings
- **Preventive care schedule** (blood tests, dental, eye exams, vaccinations)
- **Family health history** documentation

### 📋 Lab Report Processing
- **Advanced PDF parsing** with OCR fallback capability
- **Automated metric extraction** from lab reports
- **Reference range validation** for abnormality detection
- **Real-time processing pipeline** with WebSocket notifications
- **Metric standardization** for consistent data analysis
- Support for 50+ lab tests across multiple categories

**Supported Test Categories:**
- Complete Blood Count (CBC)
- Glucose & Diabetes Markers
- Lipid Profile
- Kidney Function Tests
- Liver Function Tests
- Electrolytes Panel
- Thyroid Function
- Vitamin Levels
- Coagulation Studies

### 🧠 AI-Powered Health Intelligence
- **Dynamic health index calculation** based on multiple metrics
- **Personalized recommendations** using rule-based engine
- **Trend analysis** across time periods (1D, 1W, 1M)
- **Risk assessment** with confidence scoring
- **Interactive health assistant** powered by Gemini AI
- **Natural language processing** for health queries

### 🔔 Intelligent Reminder System
- **Automated reminder generation** based on medical conditions
- **Urgency-based categorization** (Overdue, Soon, OK)
- **Customizable notification intervals**
- **Historical tracking** for completed check-ups
- **Database persistence** for registered users

### 📊 Dashboard & Analytics
- **Real-time health metrics visualization**
- **Interactive trend charts** with multiple time ranges
- **Health summary cards** with key indicators
- **Performance metrics** for ongoing health monitoring
- **Data export capabilities** in multiple formats

### 🔄 Real-Time Updates
- **WebSocket-based live notifications**
- **Automatic UI synchronization** across tabs/devices
- **Event-driven architecture** for instant updates
- **Connection pooling** for scalability
- **Graceful reconnection** on network failures

### 🌐 Multi-Language Support
- English, Hindi, Marathi language support
- **i18n implementation** for internationalization
- Dynamic language switching without page reload
- Translated health recommendations and UI elements

---

## 🏗️ Architecture

### Technology Stack

**Frontend:**
- React 18.0+ with TypeScript
- Vite (build tooling)
- Tailwind CSS (styling)
- i18n-js (internationalization)
- Axios (HTTP client)
- WebSocket API (real-time updates)

**Backend:**
- FastAPI (async web framework)
- SQLAlchemy ORM (database abstraction)
- PostgreSQL (data persistence via Neon)
- Pydantic (data validation)
- Alembic (database migrations)
- PyMuPDF/pdfplumber (PDF parsing)
- Google Gemini API (AI capabilities)

**Infrastructure:**
- Neon PostgreSQL (Cloud database)
- JWT tokens (stateless authentication)
- CORS protection (cross-origin security)
- WebSocket connections (real-time communication)

### Project Structure

```
Co-Code ggw/
├── backend/
│   ├── app/
│   │   ├── routes/              # API endpoints
│   │   │   ├── auth.py          # Authentication endpoints
│   │   │   ├── dashboard.py     # Health dashboard APIs
│   │   │   ├── recommendations.py # AI recommendations
│   │   │   ├── reports.py       # Lab report management
│   │   │   ├── health.py        # Health check endpoints
│   │   │   └── websocket.py     # WebSocket management
│   │   ├── services/            # Business logic
│   │   │   ├── metrics_service.py         # Health index computation
│   │   │   ├── recommendation_service.py  # Rule-based recommendations
│   │   │   └── enhanced_report_service.py # Report processing pipeline
│   │   ├── extraction/          # Lab data extraction
│   │   │   ├── lab_parser.py    # Metric extraction logic
│   │   │   └── pdf_extractor.py # PDF text extraction
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── db.py                # Database configuration
│   │   ├── security.py          # JWT & password utilities
│   │   ├── settings.py          # Environment configuration
│   │   └── main.py              # FastAPI application entry
│   ├── alembic/                 # Database migrations
│   ├── migrate.py               # Migration runner
│   ├── requirements.txt         # Python dependencies
│   └── start.bat                # Windows startup script
│
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable React components
│   │   │   ├── dashboard/       # Dashboard components
│   │   │   ├── health-chat/     # Chat interface
│   │   │   ├── ui/              # Generic UI components
│   │   │   └── [Feature Components]
│   │   ├── pages/               # Full-page components
│   │   │   ├── HomePage.tsx     # Landing page
│   │   │   ├── Dashboard.tsx    # Main dashboard
│   │   │   ├── HealthChat.tsx   # Chat page
│   │   │   ├── Login.tsx        # Login page
│   │   │   └── Signup.tsx       # Registration page
│   │   ├── hooks/               # Custom React hooks
│   │   │   ├── useDashboard.ts  # Dashboard data fetching
│   │   │   ├── useWebSocket.ts  # WebSocket connection
│   │   │   └── [Other Hooks]
│   │   ├── services/            # API & utility functions
│   │   │   ├── auth.ts          # Authentication API
│   │   │   └── dashboardData.ts # Dashboard utilities
│   │   ├── i18n/                # Internationalization
│   │   │   └── locales/         # Language files (en, hi, mr)
│   │   ├── App.tsx              # Main app component
│   │   ├── main.tsx             # Entry point
│   │   └── [Styling files]
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── .env.example                 # Environment template
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 16+ (with npm)
- PostgreSQL database (Neon recommended for cloud)
- Git

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your database URL, JWT secret, and API keys
   ```

5. **Run database migrations:**
   ```bash
   python migrate.py
   ```

6. **Start development server:**
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```
   Backend will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```
   Frontend will be available at `http://localhost:5175`

### Verify Installation

- Backend health check: `http://localhost:8000/api/health`
- Frontend loads: `http://localhost:5175`
- Login and test the interface

---

## 📚 API Documentation

### Authentication Endpoints

**POST** `/api/auth/register`
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "name": "John Doe"
}
```

**POST** `/api/auth/login`
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

### Health Dashboard Endpoints

**GET** `/api/health-index`
- Returns current health index score and confidence level

**GET** `/api/health-index/debug`
- Returns detailed health index computation breakdown

**GET** `/api/dashboard/trends?metric=health_index&range=1w`
- Supported metrics: `health_index`, `blood_pressure`, `glucose`, `cholesterol`
- Supported ranges: `1d`, `1w`, `1m`

**GET** `/api/recommendations`
- Returns personalized health recommendations

### Report Management Endpoints

**POST** `/api/reports/upload`
- Upload lab report PDF
- Multipart form-data with file

**GET** `/api/reports`
- List all user's reports with processing status

**GET** `/api/reports/{report_id}`
- Get detailed report information with extracted metrics

### WebSocket Connection

**WebSocket** `/ws?token=<jwt_token>`

Emitted Events:
- `health_index_updated` - Health index recalculated
- `trends_updated` - Trend data changed
- `recommendations_updated` - New recommendations available
- `reports_list_updated` - Reports list changed
- `report_parsed` - Lab report parsing complete

---

## 🔧 Configuration

### Environment Variables

Create `.env` file in backend directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Keys
GEMINI_API_KEY=your-google-gemini-api-key

# CORS
CORS_ORIGINS=http://localhost:5175,http://localhost:3000

# Server
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
DEBUG=True
```

### Database Migrations

Run pending migrations:
```bash
python migrate.py
```

Create new migration:
```bash
alembic revision --autogenerate -m "migration description"
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v
```

### Frontend Tests

```bash
cd frontend
npm run test
```

### Manual Testing Scenarios

1. **User Registration & Login**
   - Register new account
   - Login with credentials
   - Verify JWT token in localStorage

2. **Lab Report Upload**
   - Upload sample PDF report
   - Monitor processing status in WebSocket
   - Verify metrics extraction

3. **Health Dashboard**
   - View health index (should update from DB)
   - Check trends with different time ranges
   - Validate recommendations display

4. **Real-time Updates**
   - Upload report in one tab
   - Verify instant updates in other tabs
   - Check WebSocket event emission

---

## 📊 Data Models

### User Model
```python
- id: UUID (primary key)
- email: str (unique)
- password_hash: str
- name: str
- created_at: datetime
- updated_at: datetime
```

### Observation Model
```python
- id: UUID
- user_id: UUID (foreign key)
- metric_key: str (e.g., 'hemoglobin', 'glucose')
- value: float
- unit: str
- ref_range_low: float
- ref_range_high: float
- flag: str (Normal, Low, High)
- observed_at: datetime
```

### Report Model
```python
- id: UUID
- user_id: UUID
- file_path: str
- status: str (Pending, Processing, Complete, Failed)
- extracted_metrics_count: int
- created_at: datetime
- completed_at: datetime
```

---

## 🔒 Security Features

- **JWT Authentication**: Stateless, token-based authentication
- **Password Security**: Bcrypt hashing with salt
- **CORS Protection**: Restricted cross-origin requests
- **Environment Variables**: Sensitive data via .env
- **Database Encryption**: Connection via SSL/TLS
- **Input Validation**: Pydantic model validation
- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy
- **XSS Protection**: React's built-in escaping

---

## 🐛 Troubleshooting

### Backend Issues

**ImportError: No module named 'app'**
```bash
# Run from backend directory
cd backend
python -m uvicorn app.main:app --reload
```

**Database Connection Failed**
```bash
# Verify DATABASE_URL in .env
# Test connection: python -c "from app.db import engine; print('OK')"
```

**Port Already in Use**
```bash
# Use different port
python -m uvicorn app.main:app --port 8001
```

### Frontend Issues

**Module Not Found Errors**
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

**WebSocket Connection Failed**
```bash
# Check backend is running on correct port
# Verify CORS settings in backend
# Check JWT token is valid
```

---

## 📈 Performance Optimization

- **Async Database Queries**: Non-blocking I/O operations
- **PDF Parsing Fallback**: Multiple extraction methods for robustness
- **WebSocket Pooling**: Efficient connection management
- **Query Optimization**: Indexed database columns for fast retrieval
- **Frontend Lazy Loading**: Dynamic imports for code splitting
- **Caching Strategy**: Redis-compatible design for future enhancement

---

## 🔄 CI/CD Pipeline

Current deployment workflow:
1. Code commit to main branch
2. Git pushes to repository
3. Manual testing on development server
4. Production deployment ready

Recommended for production:
- GitHub Actions for automated testing
- Docker containerization
- Kubernetes orchestration
- Automated database backups

---

## 📝 API Response Format

**Success Response (200):**
```json
{
  "success": true,
  "data": { /* response payload */ }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message",
  "details": { /* error details */ }
}
```

---

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit: `git commit -m "Add feature"`
3. Push to branch: `git push origin feature/your-feature`
4. Open pull request

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 📞 Support & Contact

For issues, feature requests, or questions:
- Open an issue in the repository
- Check existing documentation
- Review error logs and troubleshooting guide

---

## 🎯 Roadmap

- [ ] Mobile app (React Native)
- [ ] Advanced ML health predictions
- [ ] Insurance integration
- [ ] Telemedicine appointment booking
- [ ] Wearable device integration
- [ ] Advanced data analytics dashboard
- [ ] Multi-tenant SaaS setup
- [ ] HIPAA compliance certification

---

**Last Updated:** January 2026  
**Version:** 1.0.0  
**Status:** Active Development
