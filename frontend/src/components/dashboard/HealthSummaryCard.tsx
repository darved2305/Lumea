/**
 * Health Summary Card
 * 
 * Shows brief health highlights and recommendations preview below health index
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { AlertCircle, CheckCircle, Info, ArrowRight } from 'lucide-react';
import { getAuthToken } from '../../utils/auth';
import './HealthSummaryCard.css';

const API_BASE = 'http://localhost:8000';

interface SummaryItem {
  type: 'positive' | 'alert' | 'focus';
  text: string;
  icon: any;
}

export default function HealthSummaryCard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<SummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasRecommendations, setHasRecommendations] = useState(false);

  useEffect(() => {
    fetchHealthSummary();
  }, []);

  const fetchHealthSummary = async () => {
    const token = getAuthToken();
    if (!token) return;

    try {
      // Fetch recommendations summary
      const response = await fetch(`${API_BASE}/api/recommendations/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setHasRecommendations(data.total_count > 0);
        
        // Build summary items
        const items: SummaryItem[] = [];
        
        // Positive highlight (always show if we have data)
        if (data.total_count === 0) {
          items.push({
            type: 'positive',
            text: 'Great! Your health profile is complete.',
            icon: CheckCircle,
          });
        } else if (data.urgent_count === 0) {
          items.push({
            type: 'positive',
            text: 'No urgent health concerns detected.',
            icon: CheckCircle,
          });
        }
        
        // Alert (if urgent recommendations exist)
        if (data.urgent_count > 0) {
          items.push({
            type: 'alert',
            text: `${data.urgent_count} high-priority ${data.urgent_count === 1 ? 'recommendation' : 'recommendations'} require attention.`,
            icon: AlertCircle,
          });
        } else if (data.warning_count > 0) {
          items.push({
            type: 'alert',
            text: `${data.warning_count} medium-priority ${data.warning_count === 1 ? 'recommendation' : 'recommendations'} available.`,
            icon: AlertCircle,
          });
        }
        
        // Focus next (general guidance)
        if (data.total_count > 0) {
          items.push({
            type: 'focus',
            text: 'Review personalized recommendations to improve your health score.',
            icon: Info,
          });
        } else {
          items.push({
            type: 'focus',
            text: 'Keep tracking your health metrics and uploading lab reports.',
            icon: Info,
          });
        }
        
        setSummary(items);
      }
    } catch (error) {
      console.error('Error fetching health summary:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return null;
  }

  return (
    <motion.div
      className="health-summary-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      <h3 className="health-summary-title">Health Highlights</h3>
      
      <div className="health-summary-list">
        {summary.map((item, index) => {
          const Icon = item.icon;
          return (
            <div key={index} className={`health-summary-item ${item.type}`}>
              <Icon size={16} />
              <span>{item.text}</span>
            </div>
          );
        })}
      </div>

      {hasRecommendations && (
        <button
          className="health-summary-cta"
          onClick={() => navigate('/recommendations')}
        >
          View Brief Recommendations
          <ArrowRight size={16} />
        </button>
      )}
    </motion.div>
  );
}
