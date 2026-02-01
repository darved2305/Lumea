import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, Share2, Upload, Wifi, WifiOff } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import DashboardNavbar from '../components/dashboard/DashboardNavbar';
import HealthIndexCard from '../components/dashboard/HealthIndexCard';
import ChatPanel from '../components/dashboard/ChatPanel';
import TrendsCard from '../components/dashboard/TrendsCard';
import RecommendationsPanel from '../components/RecommendationsPanel';
import { useWebSocket, HealthIndexUpdate } from '../hooks/useWebSocket';
import '../styles/dashboardTokens.css';
import '../styles/dashboardBase.css';
import './Dashboard.css';

const API_BASE = 'http://localhost:8000';

interface UserSummary {
  id: string;
  fullName: string;
  email: string;
  hasReports: boolean;
  healthIndex?: number;
  lastUpdated?: string;
}

function Dashboard() {
  const navigate = useNavigate();
  const [selectedFactor, setSelectedFactor] = useState<string>('index');
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [userSummary, setUserSummary] = useState<UserSummary | null>(null);
  const [healthIndex, setHealthIndex] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [recommendationsRefreshTrigger, setRecommendationsRefreshTrigger] = useState(0);

  // WebSocket for real-time updates
  const { isConnected } = useWebSocket({
    onHealthIndexUpdated: useCallback((data: HealthIndexUpdate) => {
      setHealthIndex(data.score);
      setLastUpdated(new Date(data.updated_at));
      // Refresh recommendations when health index changes
      setRecommendationsRefreshTrigger(prev => prev + 1);
    }, []),
    onReportsListUpdated: useCallback(() => {
      // Refetch user summary when reports change
      fetchUserSummary();
    }, []),
    onTrendsUpdated: useCallback(() => {
      // Trends component will handle its own refetch
    }, []),
    onRecommendationsUpdated: useCallback(() => {
      // Trigger recommendations panel refresh
      setRecommendationsRefreshTrigger(prev => prev + 1);
    }, []),
  });

  // Fetch user summary on mount
  const fetchUserSummary = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login');
      return;
    }
    setAuthToken(token);

    try {
      const response = await fetch(`${API_BASE}/api/me/bootstrap`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.status === 401) {
        localStorage.removeItem('access_token');
        navigate('/login');
        return;
      }

      if (response.ok) {
        const data = await response.json();
        setUserSummary({
          id: data.user_id,
          fullName: data.full_name,
          email: data.email,
          hasReports: data.has_reports,
          healthIndex: data.latest_health_index,
          lastUpdated: data.last_report_date,
        });
        setHealthIndex(data.latest_health_index || null);
      }
    } catch (error) {
      console.error('Error fetching user summary:', error);
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    fetchUserSummary();
  }, [fetchUserSummary]);

  const handleFactorSelect = (factor: string) => {
    setSelectedFactor(factor);
    if (window.innerWidth < 1024) {
      const trendsCard = document.querySelector('.trends-card');
      trendsCard?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const userName = userSummary?.fullName?.split(' ')[0] || 'User';
  const healthStatus = healthIndex ? `${Math.round(healthIndex)}% Healthy` : '';

  // Loading state
  if (loading) {
    return (
      <div className="dashboard-page">
        <DashboardNavbar userName="Loading..." userStatus="" />
        <div className="dashboard-content">
          <div className="dashboard-loading">
            <div className="loading-spinner" />
            <p>Loading your health data...</p>
          </div>
        </div>
      </div>
    );
  }

  // No data state - show onboarding
  if (!userSummary?.hasReports) {
    return (
      <div className="dashboard-page">
        <div className="dashboard-background">
          <div className="dashboard-bg-blob dashboard-bg-blob-1" />
          <div className="dashboard-bg-blob dashboard-bg-blob-2" />
        </div>
        <DashboardNavbar userName={userName} userStatus="" />
        
        <div className="dashboard-content">
          <div className="dashboard-container">
            <motion.div
              className="dashboard-onboarding"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div className="onboarding-card">
                <div className="onboarding-icon">
                  <Upload size={48} />
                </div>
                <h2>Welcome to Your Health Dashboard</h2>
                <p>
                  Upload your first health report to get started. We'll analyze your data 
                  and provide personalized health insights and recommendations.
                </p>
                <motion.button
                  className="dash-btn dash-btn-primary dash-btn-lg"
                  onClick={() => navigate('/reports')}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Upload size={20} />
                  Upload Your First Report
                </motion.button>
                <p className="onboarding-note">
                  Supported formats: PDF, PNG, JPG • Lab reports, blood work, medical records
                </p>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-page">
      {/* Animated Background */}
      <div className="dashboard-background">
        <div className="dashboard-bg-blob dashboard-bg-blob-1" />
        <div className="dashboard-bg-blob dashboard-bg-blob-2" />
      </div>

      {/* Navbar */}
      <DashboardNavbar userName={userName} userStatus={healthStatus} />

      {/* Main Content */}
      <div className="dashboard-content">
        <div className="dashboard-container">
          {/* Header */}
          <motion.div
            className="dashboard-header"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="dashboard-welcome">
              <div className="dashboard-welcome-text">
                <div className="welcome-title-row">
                  <h1>Welcome back, {userName}</h1>
                  <span className={`live-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
                    {isConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
                    {isConnected ? 'LIVE' : 'Offline'}
                  </span>
                </div>
                <p>
                  Your comprehensive health summary and medical insights
                  {lastUpdated && (
                    <span className="last-updated">
                      • Updated {lastUpdated.toLocaleTimeString()}
                    </span>
                  )}
                </p>
              </div>

              <div className="dashboard-quick-actions">
                <motion.button
                  className="dash-btn dash-btn-secondary dash-focus-ring"
                  onClick={() => navigate('/reports')}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <FileText size={18} />
                  Reports
                </motion.button>
                <motion.button
                  className="dash-btn dash-btn-secondary dash-focus-ring"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Download size={18} />
                  Export
                </motion.button>
                <motion.button
                  className="dash-btn dash-btn-primary dash-focus-ring"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Share2 size={18} />
                  Share
                </motion.button>
              </div>
            </div>
          </motion.div>

          {/* Top Row: Health Index + Chat */}
          <div className="dashboard-main-grid">
            <HealthIndexCard
              selectedFactor={selectedFactor}
              onFactorSelect={handleFactorSelect}
            />
            <ChatPanel />
          </div>

          {/* Recommendations Section */}
          <motion.div
            className="dashboard-full-width"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <RecommendationsPanel
              authToken={authToken || undefined}
              apiBaseUrl={API_BASE}
              maxInitialDisplay={3}
              refreshTrigger={recommendationsRefreshTrigger}
            />
          </motion.div>

          {/* Bottom Row: Trends Chart */}
          <div className="dashboard-full-width">
            <TrendsCard 
              selectedMetric={selectedFactor}
              authToken={authToken || undefined}
              apiBaseUrl={API_BASE}
              refreshTrigger={recommendationsRefreshTrigger}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
