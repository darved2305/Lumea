import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Clock, Activity, Heart, Brain, Droplet, TrendingUp, AlertCircle } from 'lucide-react';
import { useHealthSummary } from '../../hooks/useDashboard';
import type { HealthFactor } from '../../services/dashboardData';
import './HealthIndexCard.css';

interface HealthIndexCardProps {
  onFactorSelect?: (factor: string) => void;
  selectedFactor?: string;
}

const factorIcons: Record<string, React.ComponentType<any>> = {
  sleep: Brain,
  activity: Activity,
  bloodPressure: Heart,
  glucose: Droplet,
  stress: AlertCircle,
  hydration: Droplet,
};

function HealthIndexCard({ onFactorSelect, selectedFactor }: HealthIndexCardProps) {
  const { data: healthData, loading } = useHealthSummary();
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    if (healthData) {
      // Animate score from 0 to actual value
      const duration = 1500;
      const steps = 60;
      const increment = healthData.healthIndexScore / steps;
      let current = 0;

      const timer = setInterval(() => {
        current += increment;
        if (current >= healthData.healthIndexScore) {
          setAnimatedScore(healthData.healthIndexScore);
          clearInterval(timer);
        } else {
          setAnimatedScore(Math.floor(current));
        }
      }, duration / steps);

      return () => clearInterval(timer);
    }
  }, [healthData]);

  if (loading || !healthData) {
    return (
      <div className="dash-card health-index-card">
        <div className="dash-card-header">
          <h2 className="dash-card-title">Health Index</h2>
        </div>
        <div className="dash-card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '400px' }}>
          <div style={{ textAlign: 'center', color: 'var(--dash-text-muted)' }}>
            Loading...
          </div>
        </div>
      </div>
    );
  }

  const circumference = 2 * Math.PI * 110; // radius = 110
  const progress = (animatedScore / 100) * circumference;

  return (
    <motion.div
      className="dash-card health-index-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="dash-card-header">
        <h2 className="dash-card-title">Health Index</h2>
        <div className="health-index-meta">
          <span className="dash-badge dash-badge-live">
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor' }}></div>
            LIVE
          </span>
        </div>
      </div>

      {/* Score Circle */}
      <div className="health-index-score-section">
        <div className="health-index-circle-container">
          <svg
            className="health-index-circle"
            width="240"
            height="240"
            viewBox="0 0 240 240"
          >
            <defs>
              <linearGradient id="healthGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#6b9175" />
                <stop offset="100%" stopColor="#4a7c59" />
              </linearGradient>
            </defs>
            
            {/* Background Circle */}
            <circle
              className="health-index-circle-bg"
              cx="120"
              cy="120"
              r="110"
            />
            
            {/* Progress Circle */}
            <circle
              className="health-index-circle-progress"
              cx="120"
              cy="120"
              r="110"
              strokeDasharray={circumference}
              strokeDashoffset={circumference - progress}
            />
          </svg>

          <div className="health-index-score-value">
            <div className="health-index-score-number">{animatedScore}</div>
            <div className="health-index-score-label">Health Score</div>
          </div>
        </div>

        <div className="health-index-meta">
          <span className="health-index-updated">
            <Clock size={14} />
            Last updated: just now
          </span>
          <span className="health-index-updated" style={{ color: 'var(--dash-accent-dark)' }}>
            <TrendingUp size={14} />
            {healthData.trend === 'up' ? 'Improving' : healthData.trend === 'down' ? 'Declining' : 'Stable'}
          </span>
        </div>
      </div>

      {/* Factors List */}
      <div className="health-index-factors-section dash-scrollbar">
        <h3 className="health-index-factors-title">What's Affecting Your Score</h3>
        <div className="health-index-factors-list">
          {healthData.factors.map((factor: HealthFactor) => {
            const Icon = factorIcons[factor.key] || Activity;
            return (
              <motion.div
                key={factor.key}
                className={`health-factor-item ${selectedFactor === factor.key ? 'selected' : ''}`}
                onClick={() => onFactorSelect?.(factor.key)}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
              >
                <div className="health-factor-header">
                  <div className="health-factor-info">
                    <div className={`health-factor-icon ${factor.status}`}>
                      <Icon size={18} />
                    </div>
                    <span className="health-factor-label">{factor.label}</span>
                  </div>
                  <span className="health-factor-contribution">
                    {factor.contribution}%
                  </span>
                </div>
                
                <div className="health-factor-progress">
                  <div className="health-factor-bar">
                    <motion.div
                      className={`health-factor-bar-fill ${factor.status}`}
                      initial={{ width: 0 }}
                      animate={{ width: `${factor.value}%` }}
                      transition={{ duration: 1, delay: 0.3 }}
                    />
                  </div>
                  <span className="health-factor-value">{factor.value}</span>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}

export default HealthIndexCard;
