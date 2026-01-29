# Co-Code GGW - Unified Medical Companion Platform

A comprehensive health companion platform that enables users to manage preventive health checkups, receive personalized health reminders, and interact with an intelligent health assistant. The platform supports both guest users and registered members with persistent data management.

---

## 📋 Overview

Co-Code GGW is a full-stack health technology platform designed to improve preventive care management. The application provides:

- **Dual User Access**: Guest mode for quick intake, registered mode for full feature access
- **Intelligent Reminders**: Automated health checkup reminders based on user profiles and medical conditions
- **AI Health Assistant**: Interactive chat interface for health-related queries
- **Secure Authentication**: JWT-based authentication with secure password storage
- **Responsive Design**: Modern UI matching contemporary design standards

---

## ✨ Key Features

### User Management
- User registration with email and password
- JWT-based authentication with httpOnly cookie storage
- Role-based access control
- User profile management

### Health Profile Management
- Comprehensive health intake forms
- BMI calculation and tracking
- Medical condition tracking
- Medication and allergy documentation
- Preventive care tracking (blood tests, dental, eye exams)

### Reminder Engine
- Automated health checkup reminders based on medical conditions
- Customizable reminder intervals
- Urgency-based categorization (Overdue, Soon, OK)
- Database-backed persistence for registered users

### Chat Interface
- Real-time health-related queries
- Message history and persistence
- Support for both guest and authenticated conversations
- Session-based chat management

### Data Persistence
- Guest users: localStorage-based persistence
- Registered users: PostgreSQL database persistence
- Secure data transmission with CORS protection

---

## 🛠️ Technology Stack

### Backend
| Component | Technology |
|-----------|------------|
| Framework | FastAPI 0.104+ |
| Database | PostgreSQL 14+ |
| ORM | SQLAlchemy 2.0 (async) |
| Driver | asyncpg |
| Authentication | JWT (python-jose) + bcrypt |
| Validation | Pydantic v2 |

### Frontend
| Component | Technology |
|-----------|------------|
| Framework | React 18 + TypeScript |
| Build Tool | Vite |
| Routing | React Router v7 |
| Animations | Framer Motion |
| HTTP Client | Fetch API with credentials |
| Styling | CSS3 with design system |

---

## 📁 Project Structure

```
Co-Code GGW/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application setup
│   │   ├── db.py                   # Database connection pool
│   │   ├── models.py               # SQLAlchemy data models
│   │   ├── schemas.py              # Pydantic request/response schemas
│   │   ├── security.py             # Authentication & password hashing
│   │   ├── settings.py             # Environment configuration
│   │   ├── reminders.py            # Health reminder computation logic
│   │   └── routes/
│   │       ├── auth.py             # Authentication endpoints
│   │       └── health.py           # Health chat & profile endpoints
│   ├── migrate.py                  # Database migration script
│   ├── requirements.txt
│   ├── start.bat
│   └── .env.example
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── ui/                 # Reusable UI components
    │   │   │   ├── Button.tsx
    │   │   │   ├── Input.tsx
    │   │   │   └── Card.tsx
    │   │   ├── health-chat/        # Health chat feature components
    │   │   │   ├── GuestIntakeForm.tsx
    │   │   │   ├── ChatPanel.tsx
    │   │   │   ├── SnapshotPanel.tsx
    │   │   │   └── RemindersPanel.tsx
    │   │   └── [Other components]
    │   ├── pages/
    │   │   ├── HomePage.tsx
    │   │   ├── Login.tsx
    │   │   ├── Signup.tsx
    │   │   └── HealthChat.tsx      # Main health chat page
    │   ├── services/
    │   │   └── auth.ts             # API service layer
    │   ├── App.tsx
    │   └── main.tsx
    ├── package.json
    ├── tsconfig.json
    └── vite.config.ts
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- Node.js 18 or higher
- PostgreSQL 14 or higher (or Neon/Supabase for cloud)

### Backend Setup

1. **Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with required values:
   ```env
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/cocode_ggw
   JWT_SECRET=your-secure-random-key-here
   FRONTEND_ORIGIN=http://localhost:5173
   ```

3. **Create Database**
   ```bash
   createdb cocode_ggw
   ```

4. **Run Database Migrations**
   ```bash
   python migrate.py
   ```

5. **Start Backend Server**
   ```bash
   # Windows
   start.bat
   
   # Linux/macOS
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   Server runs at: http://localhost:8000  
   API Documentation: http://localhost:8000/docs

### Frontend Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start Development Server**
   ```bash
   npm run dev
   ```
   
   Application available at: http://localhost:5173

---

## 📡 API Reference

### Authentication Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|-----------------|
| POST | `/api/auth/register` | Create new user account | None |
| POST | `/api/auth/login` | Authenticate user | None |
| POST | `/api/auth/logout` | Clear authentication | Cookie |

### User Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|-----------------|
| GET | `/api/me` | Retrieve current user info | Required |

### Health Profile Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|-----------------|
| GET | `/api/profile` | Retrieve user health profile | Required |
| POST | `/api/profile` | Create health profile | Required |
| PUT | `/api/profile` | Update health profile | Required |

### Health Features Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|-----------------|
| GET | `/api/reminders` | Get computed health reminders | Required |
| POST | `/api/chat` | Send chat message | Required/Optional* |
| GET | `/api/chat/history` | Retrieve chat history | Required/Optional* |

*Works for authenticated users and guests (requires guest_key)

---

## 🗄️ Database Schema

### Users Table
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(255),
  created_at TIMESTAMP,
  last_login_at TIMESTAMP
);
```

### Patient Profiles Table
```sql
CREATE TABLE patient_profiles (
  id UUID PRIMARY KEY,
  user_id UUID UNIQUE REFERENCES users(id),
  age INTEGER,
  gender VARCHAR(20),
  height_cm FLOAT,
  weight_kg FLOAT,
  bmi FLOAT,
  conditions TEXT[],
  last_blood_test_at TIMESTAMP,
  last_dental_at TIMESTAMP,
  last_eye_exam_at TIMESTAMP,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Chat Sessions Table
```sql
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  guest_key VARCHAR(255),
  created_at TIMESTAMP
);
```

### Chat Messages Table
```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES chat_sessions(id),
  role VARCHAR(50),
  content TEXT,
  created_at TIMESTAMP
);
```

---

## 🔔 Health Reminder System

The system computes preventive care reminders based on:

| Condition | Recommendation | Interval |
|-----------|-----------------|----------|
| General Health | Blood Work | 12 months |
| General Health | Dental Checkup | 6 months |
| General Health | Eye Examination | 12 months |
| Diabetes | HbA1c Test | 3 months |
| Hypertension | Kidney Function | 6 months |
| Diabetes | Kidney Function | 6 months |

### Urgency Levels
- **Overdue**: Past scheduled date
- **Soon**: Due within 30 days
- **OK**: Scheduled beyond 30 days

---

## 👥 User Flows

### Guest User Flow
1. Navigate to `/health-chat`
2. Complete optional health intake form
3. Profile stored in browser localStorage
4. Use chat interface immediately
5. Option to save profile by creating account

### Registered User Flow
1. Register or login at `/signup` or `/login`
2. JWT authentication token stored in httpOnly cookie
3. Automatically redirected to `/health-chat`
4. Health profile auto-loaded from database
5. View personalized health reminders
6. Full chat history and profile persistence

---

## 🎨 Design System

### Color Palette
- **Primary**: #4a7c59 (Forest Green)
- **Background**: #f5f0e8 (Warm Beige)
- **Text Primary**: #2d2d2d (Dark Gray)
- **Text Secondary**: #5a5a5a (Medium Gray)
- **Accent**: #7a7a7a (Light Gray)
- **Error**: #d64545 (Red)
- **Warning**: #f59e0b (Amber)

### Typography
- **Headings**: Cormorant Garamond, serif
- **Body**: DM Sans, sans-serif

### Component Guidelines
- Border Radius: 8-16px
- Animations: Framer Motion with 300-500ms duration
- Shadows: Subtle elevation system
- Spacing: 8px base unit system

---

## ✅ Testing Guide

### Manual Test Cases

**Guest Mode**
- [ ] Access `/health-chat` → intake form displays
- [ ] Complete health form → BMI calculates correctly
- [ ] Submit form → chat interface loads
- [ ] View snapshot panel showing profile
- [ ] Verify reminders computed and displayed
- [ ] Send chat messages
- [ ] Refresh page → data persists from localStorage

**Registered Mode**
- [ ] Complete registration → redirects to health chat
- [ ] Login → auth cookie stored
- [ ] Visit `/health-chat` → profile auto-populated
- [ ] Update profile → changes saved to database
- [ ] Verify reminders update based on profile
- [ ] Chat history persists across sessions
- [ ] Logout → auth cleared

**Quality Assurance**
- [ ] UI matches design system
- [ ] Animations perform smoothly (60fps)
- [ ] Mobile responsive (320px+)
- [ ] Loading states display correctly
- [ ] Error messages informative and styled

---

## 🔒 Security Considerations

### Authentication
- JWT tokens stored in httpOnly cookies (CSRF protected)
- Passwords hashed with bcrypt (salt rounds: 12)
- CORS configured for frontend origin only
- Cache-Control headers prevent sensitive data caching

### Data Protection
- All user data scoped to authenticated user
- Database queries parameterized to prevent SQL injection
- Input validation via Pydantic schemas
- Sensitive headers not exposed to frontend

### Production Deployment
- [ ] Use HTTPS only (secure cookie flag)
- [ ] Rotate JWT_SECRET regularly
- [ ] Enable database SSL connections
- [ ] Implement rate limiting
- [ ] Configure WAF rules
- [ ] Set up monitoring and alerts

---

## 📦 Deployment

### Environment Variables (Production)
```env
DATABASE_URL=postgresql+asyncpg://user:password@prod-host:5432/db
JWT_SECRET=<generate-64-char-secure-key>
FRONTEND_ORIGIN=https://yourdomain.com
ENVIRONMENT=production
```

### Deployment Checklist
- [ ] Database backups enabled
- [ ] Monitoring and logging configured
- [ ] SSL certificates installed
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Error tracking (Sentry, etc.) set up
- [ ] Performance monitoring active

---

## 🚦 Status & Roadmap

### Current Release (v1.0)
- ✅ User authentication (register/login/logout)
- ✅ Health profile management
- ✅ Chat interface (guest + registered)
- ✅ Reminder system
- ✅ Responsive UI

### Future Enhancements
- [ ] Real AI integration (OpenAI/Claude API)
- [ ] Document upload and PDF parsing
- [ ] Email/SMS notifications
- [ ] Calendar integration
- [ ] Multi-language support
- [ ] Dark mode
- [ ] Advanced analytics dashboard
- [ ] Medication tracking
- [ ] Appointment scheduling

---

## 📝 License

Copyright © 2026 Co-Code GGW. All rights reserved.

---

## 📞 Support

For issues, feature requests, or technical support, please contact the development team.

---

**Built with modern technologies for optimal health management**
