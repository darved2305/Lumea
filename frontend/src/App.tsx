import { lazy, Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import './App.css'

// Lazy load pages
const HomePage = lazy(() => import('./pages/HomePage'))
const Login = lazy(() => import('./pages/Login'))
const Signup = lazy(() => import('./pages/Signup'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Reports = lazy(() => import('./pages/Reports'))
const ReportSummary = lazy(() => import('./pages/ReportSummary'))
const HealthProfile = lazy(() => import('./pages/HealthProfile'))
const Settings = lazy(() => import('./pages/Settings'))
const Recommendations = lazy(() => import('./pages/Recommendations'))
const Medicines = lazy(() => import('./pages/Medicines'))
const VoiceAgent = lazy(() => import('./pages/VoiceAgent'))
const Features = lazy(() => import('./pages/Features'))
const PhysicsTwin = lazy(() => import('./pages/PhysicsTwin'))

// Loading fallback
const PageLoading = () => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    backgroundColor: '#f5f0e8',
    color: '#6b9175',
    fontFamily: '"DM Sans", sans-serif'
  }}>
    <div>Loading Lumea...</div>
  </div>
)

function App() {
  return (
    <Router>
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <ProtectedRoute>
                <Reports />
              </ProtectedRoute>
            }
          />
          <Route
            path="/report-summary"
            element={
              <ProtectedRoute>
                <ReportSummary />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recommendations"
            element={
              <ProtectedRoute>
                <Recommendations />
              </ProtectedRoute>
            }
          />
          <Route
            path="/medicines"
            element={
              <ProtectedRoute>
                <Medicines />
              </ProtectedRoute>
            }
          />
          <Route
            path="/voice-agent"
            element={
              <ProtectedRoute>
                <VoiceAgent />
              </ProtectedRoute>
            }
          />
          <Route
            path="/physics-twin"
            element={
              <ProtectedRoute>
                <PhysicsTwin />
              </ProtectedRoute>
            }
          />
          <Route
            path="/health-profile"
            element={
              <ProtectedRoute>
                <HealthProfile />
              </ProtectedRoute>
            }
          />
          <Route
            path="/features"
            element={
              <ProtectedRoute>
                <Features />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            }
          />
          {/* Catch-all: redirect unknown routes to home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </Router>
  )
}

export default App
