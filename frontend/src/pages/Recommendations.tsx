/**
 * Recommendations Page
 * 
 * Displays personalized health recommendations using the shared RecommendationsPanel component.
 * Matches dashboard UI/UX styling.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import DashboardNavbar from '../components/dashboard/DashboardNavbar';
import RecommendationsPanel from '../components/RecommendationsPanel';
import { getAuthToken } from '../utils/auth';
import '../styles/dashboardTokens.css';
import '../styles/dashboardBase.css';
import './Recommendations.css';

const API_BASE = 'http://localhost:8000';

export default function Recommendations() {
  const navigate = useNavigate();
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [userName, setUserName] = useState<string>('User');
  const [loading, setLoading] = useState(true);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      navigate('/login');
      return;
    }
    setAuthToken(token);
    
    // Fetch user info
    fetch(`${API_BASE}/api/me/bootstrap`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data?.full_name) {
          setUserName(data.full_name.split(' ')[0]);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [navigate]);

  if (loading) {
    return (
      <div className="recommendations-page dashboard-page">
        <DashboardNavbar userName="Loading..." userStatus="" />
        <div className="recommendations-loading">
          <div className="loading-spinner" />
          <p>Loading recommendations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="recommendations-page dashboard-page">
      {/* Background matching dashboard */}
      <div className="dashboard-background">
        <div className="dashboard-bg-blob dashboard-bg-blob-1" />
        <div className="dashboard-bg-blob dashboard-bg-blob-2" />
      </div>

      <DashboardNavbar userName={userName} userStatus="" />
      
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
                <h1>Health Recommendations</h1>
                <p>Personalized insights based on your health profile and reports</p>
              </div>
            </div>
          </motion.div>

          {/* Recommendations Panel - using shared component */}
          <motion.div
            className="dashboard-full-width"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <RecommendationsPanel
              authToken={authToken || undefined}
              apiBaseUrl={API_BASE}
              maxInitialDisplay={20}
              refreshTrigger={refreshTrigger}
              showGenerateButton={true}
              onRecommendationsGenerated={() => setRefreshTrigger(prev => prev + 1)}
              variant="page"
            />
          </motion.div>
        </div>
      </div>
    </div>
  );
}
