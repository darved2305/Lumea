import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, Share2 } from 'lucide-react';
import DashboardNavbar from '../components/dashboard/DashboardNavbar';
import HealthIndexCard from '../components/dashboard/HealthIndexCard';
import ChatPanel from '../components/dashboard/ChatPanel';
import TrendsCard from '../components/dashboard/TrendsCard';
import '../styles/dashboardTokens.css';
import '../styles/dashboardBase.css';
import './Dashboard.css';

function Dashboard() {
  const [selectedFactor, setSelectedFactor] = useState<string>('index');

  const handleFactorSelect = (factor: string) => {
    setSelectedFactor(factor);
    // Scroll to trends card on mobile
    if (window.innerWidth < 1024) {
      const trendsCard = document.querySelector('.trends-card');
      trendsCard?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="dashboard-page">
      {/* Animated Background */}
      <div className="dashboard-background">
        <div className="dashboard-bg-blob dashboard-bg-blob-1" />
        <div className="dashboard-bg-blob dashboard-bg-blob-2" />
      </div>

      {/* Navbar */}
      <DashboardNavbar userName="Willian" userStatus="71% Healthy" />

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
                <h1>Welcome back, Willian! 👋</h1>
                <p>Here's your health overview for today</p>
              </div>

              <div className="dashboard-quick-actions">
                <motion.button
                  className="dash-btn dash-btn-secondary dash-focus-ring"
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

          {/* Bottom Row: Trends Chart */}
          <div className="dashboard-full-width">
            <TrendsCard selectedMetric={selectedFactor} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
