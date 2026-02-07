/**
 * RecommendationsCard – dynamic recommendations based on detected conditions.
 *
 * Shows condition-specific recommendations with curated YouTube links.
 * "Show more" toggle for overflow.
 */

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Youtube,
  Heart,
  Shield,
} from 'lucide-react';
import type { DetectedConditionFE, Severity } from './BodyImpactOverlay';

// ---------- Types ----------

interface RecommendationsCardProps {
  conditions: DetectedConditionFE[];
}

// ---------- Severity styling ----------

const SEVERITY_CONFIG: Record<Severity, { icon: React.ReactNode; label: string; cssClass: string }> = {
  severe:   { icon: <AlertTriangle size={14} />, label: 'Severe',   cssClass: 'danger' },
  moderate: { icon: <AlertCircle size={14} />,   label: 'Moderate', cssClass: 'warning' },
  mild:     { icon: <Info size={14} />,          label: 'Mild',     cssClass: 'info' },
};

// ---------- YouTube search URL builder ----------

function youtubeSearchUrl(query: string): string {
  return `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
}

// ---------- Condition card ----------

interface ConditionBlockProps {
  condition: DetectedConditionFE;
  isExpanded: boolean;
  onToggle: () => void;
}

function ConditionBlock({ condition, isExpanded, onToggle }: ConditionBlockProps) {
  const cfg = SEVERITY_CONFIG[condition.severity];
  const [showAllRecs, setShowAllRecs] = useState(false);
  const maxVisible = 3;
  const visibleRecs = showAllRecs ? condition.recommendations : condition.recommendations.slice(0, maxVisible);
  const hasMore = condition.recommendations.length > maxVisible;

  return (
    <div className={`reco-condition-block reco-condition-${cfg.cssClass}`}>
      {/* Header */}
      <button className="reco-condition-header" onClick={onToggle}>
        <div className="reco-condition-header-left">
          {cfg.icon}
          <span className="reco-condition-name">{condition.name}</span>
          <span className={`dash-badge dash-badge-${cfg.cssClass}`}>{cfg.label}</span>
        </div>
        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {/* Expanded content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            className="reco-condition-body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            <p className="reco-condition-desc">{condition.description}</p>

            {/* Trigger metrics */}
            <div className="reco-triggers">
              {Object.entries(condition.trigger_metrics).map(([metric, val]) => (
                <span key={metric} className="reco-trigger-chip">
                  {metric.replace(/_/g, ' ')}: <strong>{typeof val === 'number' ? val.toFixed(1) : val}</strong>
                </span>
              ))}
            </div>

            {/* Recommendations */}
            <div className="reco-list">
              <h4 className="reco-list-title">Recommendations</h4>
              {visibleRecs.map((rec, i) => (
                <div key={i} className="reco-item">
                  <Shield size={12} />
                  <span>{rec}</span>
                </div>
              ))}
              {hasMore && (
                <button
                  className="reco-show-more"
                  onClick={(e) => { e.stopPropagation(); setShowAllRecs(!showAllRecs); }}
                >
                  {showAllRecs ? 'Show less' : `Show ${condition.recommendations.length - maxVisible} more`}
                </button>
              )}
            </div>

            {/* YouTube links */}
            {condition.youtube_queries.length > 0 && (
              <div className="reco-youtube">
                <h4 className="reco-list-title">
                  <Youtube size={14} />
                  Learn More
                </h4>
                <div className="reco-youtube-links">
                  {condition.youtube_queries.map((q, i) => (
                    <a
                      key={i}
                      href={youtubeSearchUrl(q)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="reco-youtube-link"
                    >
                      <Youtube size={12} />
                      {q}
                      <ExternalLink size={10} />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------- Main component ----------

const RecommendationsCard: React.FC<RecommendationsCardProps> = ({ conditions }) => {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Auto-expand first condition
  useMemo(() => {
    if (conditions.length > 0 && expandedIds.size === 0) {
      setExpandedIds(new Set([conditions[0].id]));
    }
  }, [conditions]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (conditions.length === 0) {
    return (
      <div className="dash-card physics-recommendations-card">
        <div className="dash-card-header">
          <h3 className="dash-card-title">
            <Heart size={18} />
            Recommendations
          </h3>
        </div>
        <div className="dash-card-body">
          <div className="reco-empty">
            <Shield size={32} />
            <p>All vitals within normal range</p>
            <span className="reco-empty-sub">Keep up your healthy habits!</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dash-card physics-recommendations-card">
      <div className="dash-card-header">
        <h3 className="dash-card-title">
          <Heart size={18} />
          Recommendations
        </h3>
        <span className="dash-badge dash-badge-warning">
          {conditions.length} alert{conditions.length > 1 ? 's' : ''}
        </span>
      </div>
      <div className="dash-card-body reco-body">
        {conditions.map((cond) => (
          <ConditionBlock
            key={cond.id}
            condition={cond}
            isExpanded={expandedIds.has(cond.id)}
            onToggle={() => toggleExpand(cond.id)}
          />
        ))}

        <div className="reco-disclaimer">
          <Info size={12} />
          <span>
            These are informational suggestions based on metric patterns.
            Always consult a healthcare professional for medical decisions.
          </span>
        </div>
      </div>
    </div>
  );
};

export default RecommendationsCard;
