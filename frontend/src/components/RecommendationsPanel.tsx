import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Lightbulb,
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Shield,
  RefreshCw,
  CheckCircle2,
  Dumbbell,
  Apple,
  Moon,
  Heart,
  Droplets,
  TestTube,
  Stethoscope,
  Sparkles,
  XCircle,
} from 'lucide-react';
import './RecommendationsPanel.css';

// Types
interface Action {
  type: string;
  text: string;
}

interface Source {
  name: string;
  url?: string;
}

interface Recommendation {
  id: string;
  title: string;
  severity: 'URGENT' | 'WARNING' | 'INFO';
  why: string;
  actions: Action[];
  followup: Action[];
  sources: Source[];
}

interface RecommendationsResponse {
  updated_at: string;
  disclaimer: string;
  items: Recommendation[];
  total_count: number;
  urgent_count: number;
  warning_count: number;
}

interface RecommendationsPanelProps {
  authToken?: string;
  apiBaseUrl?: string;
  maxInitialDisplay?: number;
  refreshTrigger?: number; // Increment this to trigger a refresh (from WebSocket events)
  showGenerateButton?: boolean; // Show generate button for generating new recommendations
  onRecommendationsGenerated?: () => void; // Callback after generating recommendations
  variant?: 'dashboard' | 'page'; // Layout variant
}

// Action type to icon mapping
const actionIcons: Record<string, React.ReactNode> = {
  EXERCISE: <Dumbbell size={14} />,
  DIET: <Apple size={14} />,
  HABIT: <Sparkles size={14} />,
  SLEEP: <Moon size={14} />,
  STRESS: <Heart size={14} />,
  HYDRATION: <Droplets size={14} />,
  TEST: <TestTube size={14} />,
  DOCTOR: <Stethoscope size={14} />,
  GENERAL: <CheckCircle2 size={14} />,
};

// Severity icons
const severityIcons: Record<string, React.ReactNode> = {
  URGENT: <AlertCircle size={18} />,
  WARNING: <AlertTriangle size={18} />,
  INFO: <Info size={18} />,
};

const RecommendationsPanel: React.FC<RecommendationsPanelProps> = ({
  authToken,
  apiBaseUrl = 'http://localhost:8000',
  maxInitialDisplay = 3,
  refreshTrigger = 0,
  showGenerateButton = true,
  onRecommendationsGenerated,
  variant = 'dashboard',
}) => {
  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());

  const fetchRecommendations = useCallback(async () => {
    if (!authToken) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/recommendations`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch recommendations: ${response.status}`);
      }

      const data: RecommendationsResponse = await response.json();
      setRecommendations(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recommendations');
    } finally {
      setLoading(false);
    }
  }, [authToken, apiBaseUrl]);

  useEffect(() => {
    fetchRecommendations();
  }, [fetchRecommendations]);

  // Refresh when refreshTrigger changes (triggered by WebSocket events from parent)
  useEffect(() => {
    if (refreshTrigger > 0) {
      fetchRecommendations();
    }
  }, [refreshTrigger, fetchRecommendations]);

  // Generate new recommendations
  const handleGenerateRecommendations = async () => {
    if (!authToken) return;
    
    setGenerating(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/recommendations/generate`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        // Refresh recommendations after generating
        await fetchRecommendations();
        onRecommendationsGenerated?.();
      }
    } catch (err) {
      console.error('Error generating recommendations:', err);
    } finally {
      setGenerating(false);
    }
  };

  const toggleCardExpanded = (id: string) => {
    setExpandedCards(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const displayedItems = recommendations?.items.slice(
    0,
    expanded ? undefined : maxInitialDisplay
  ) || [];

  const hasMore = (recommendations?.items.length || 0) > maxInitialDisplay;

  if (loading) {
    return (
      <div className="recommendations-panel">
        <div className="recommendations-loading">
          <div className="spinner" />
          <p>Loading personalized recommendations...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="recommendations-panel">
        <div className="recommendations-error">
          <XCircle size={48} />
          <p>{error}</p>
          <button className="retry-button" onClick={fetchRecommendations}>
            <RefreshCw size={16} />
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!recommendations || recommendations.items.length === 0) {
    return (
      <div className={`recommendations-panel ${variant === 'page' ? 'recommendations-panel-page' : ''}`}>
        <div className="recommendations-header">
          <h2>
            <Lightbulb size={22} />
            Recommendations
          </h2>
          {showGenerateButton && (
            <button
              className="recommendations-generate-btn"
              onClick={handleGenerateRecommendations}
              disabled={generating}
            >
              {generating ? (
                <><RefreshCw size={16} className="spinning" /> Generating...</>
              ) : (
                <><Sparkles size={16} /> Generate</>               )}
            </button>
          )}
        </div>
        <div className="recommendations-empty">
          <Sparkles size={48} />
          <h3>No recommendations yet</h3>
          <p>
            Generate personalized recommendations based on your health profile and reports.
          </p>
          {showGenerateButton && (
            <button
              className="recommendations-generate-btn recommendations-generate-btn-lg"
              onClick={handleGenerateRecommendations}
              disabled={generating}
            >
              {generating ? (
                <><RefreshCw size={18} className="spinning" /> Generating...</>
              ) : (
                <><Sparkles size={18} /> Generate Recommendations</>               )}
            </button>
          )}
        </div>
        <div className="recommendations-disclaimer">
          <Shield size={18} />
          <p>{recommendations?.disclaimer || 'This is wellness guidance, not medical advice.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`recommendations-panel ${variant === 'page' ? 'recommendations-panel-page' : ''}`}>
      <div className="recommendations-header">
        <div className="recommendations-header-left">
          <h2>
            <Lightbulb size={22} />
            Recommendations
          </h2>
          {showGenerateButton && (
            <button
              className="recommendations-generate-btn"
              onClick={handleGenerateRecommendations}
              disabled={generating}
            >
              {generating ? (
                <><RefreshCw size={16} className="spinning" /> Generating...</>
              ) : (
                <><RefreshCw size={16} /> Refresh</>               )}
            </button>
          )}
        </div>
        <div className="recommendations-badges">
          {recommendations.urgent_count > 0 && (
            <span className="badge urgent">
              <AlertCircle size={14} />
              {recommendations.urgent_count} Urgent
            </span>
          )}
          {recommendations.warning_count > 0 && (
            <span className="badge warning">
              <AlertTriangle size={14} />
              {recommendations.warning_count} Attention
            </span>
          )}
          {recommendations.total_count - recommendations.urgent_count - recommendations.warning_count > 0 && (
            <span className="badge info">
              <Info size={14} />
              {recommendations.total_count - recommendations.urgent_count - recommendations.warning_count} Tips
            </span>
          )}
        </div>
      </div>

      <div className="recommendations-list">
        <AnimatePresence mode="popLayout">
          {displayedItems.map((item, index) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ delay: index * 0.05 }}
              className={`recommendation-card ${item.severity.toLowerCase()}`}
            >
              <div className="recommendation-header">
                <h3 className="recommendation-title">{item.title}</h3>
                <span className={`severity-tag ${item.severity.toLowerCase()}`}>
                  {severityIcons[item.severity]}
                  {item.severity}
                </span>
              </div>

              <p className="recommendation-why">{item.why}</p>

              <div className="recommendation-actions">
                <h4>Suggested Actions</h4>
                <div className="actions-list">
                  {item.actions.slice(0, expandedCards.has(item.id) ? undefined : 3).map((action, idx) => (
                    <span key={idx} className={`action-tag ${action.type.toLowerCase()}`}>
                      {actionIcons[action.type] || <ChevronRight size={14} />}
                      {action.text}
                    </span>
                  ))}
                  {item.actions.length > 3 && !expandedCards.has(item.id) && (
                    <button
                      className="action-tag"
                      onClick={() => toggleCardExpanded(item.id)}
                      style={{ cursor: 'pointer', background: '#f0f0f0' }}
                    >
                      +{item.actions.length - 3} more
                    </button>
                  )}
                </div>
              </div>

              {item.followup.length > 0 && (
                <div className="recommendation-followup">
                  <h4>Follow-up</h4>
                  <div className="followup-list">
                    {item.followup.map((follow, idx) => (
                      <div key={idx} className="followup-item">
                        {actionIcons[follow.type] || <ChevronRight size={14} />}
                        {follow.text}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {item.sources.length > 0 && expandedCards.has(item.id) && (
                <div className="recommendation-sources">
                  <div className="sources-list">
                    {item.sources.map((source, idx) => (
                      source.url ? (
                        <a
                          key={idx}
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="source-link"
                        >
                          📎 {source.name}
                        </a>
                      ) : (
                        <span key={idx} className="source-link">
                          📎 {source.name}
                        </span>
                      )
                    ))}
                  </div>
                </div>
              )}

              {(item.actions.length > 3 || item.sources.length > 0) && (
                <button
                  className="expand-toggle"
                  onClick={() => toggleCardExpanded(item.id)}
                  style={{ marginTop: '12px' }}
                >
                  {expandedCards.has(item.id) ? (
                    <>
                      <ChevronUp size={16} />
                      Show less
                    </>
                  ) : (
                    <>
                      <ChevronDown size={16} />
                      Show more details
                    </>
                  )}
                </button>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {hasMore && (
        <button className="expand-toggle" onClick={() => setExpanded(!expanded)}>
          {expanded ? (
            <>
              <ChevronUp size={16} />
              Show fewer recommendations
            </>
          ) : (
            <>
              <ChevronDown size={16} />
              Show {recommendations.items.length - maxInitialDisplay} more recommendations
            </>
          )}
        </button>
      )}

      <div className="recommendations-disclaimer">
        <Shield size={18} />
        <p>{recommendations.disclaimer}</p>
      </div>
    </div>
  );
};

export default RecommendationsPanel;
