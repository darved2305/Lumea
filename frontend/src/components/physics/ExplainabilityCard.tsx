/**
 * ExplainabilityCard – deterministic scoring breakdown.
 * Shows weights, normalised contributions, coverage/confidence.
 * Styled to match the calm Lumea card aesthetic.
 */

import React from 'react';
import { Info, BarChart3 } from 'lucide-react';
import type { OrganResult } from '../../services/physicsApi';

interface ExplainabilityCardProps {
  selectedOrgan: string | null;
  organResult: OrganResult | null;
  organLabel: string;
}

const ExplainabilityCard: React.FC<ExplainabilityCardProps> = ({
  selectedOrgan,
  organResult,
  organLabel,
}) => {
  if (!selectedOrgan || !organResult) {
    return (
      <div className="dash-card physics-explainability-card">
        <div className="dash-card-header">
          <h3 className="dash-card-title">
            <BarChart3 size={18} />
            Explainability
          </h3>
        </div>
        <div className="dash-card-body">
          <div className="physics-explain-empty">
            <Info size={32} />
            <p>Select an organ to see the scoring breakdown</p>
          </div>
        </div>
      </div>
    );
  }

  const presentMetrics = organResult.contributions.filter((c) => c.value != null);
  const totalWeight = organResult.contributions.reduce((s, c) => s + c.weight, 0);
  const presentWeight = presentMetrics.reduce((s, c) => s + c.weight, 0);

  return (
    <div className="dash-card physics-explainability-card">
      <div className="dash-card-header">
        <h3 className="dash-card-title">
          <BarChart3 size={18} />
          Why this score?
        </h3>
        <span className="physics-explain-organ-badge">{organLabel}</span>
      </div>

      <div className="dash-card-body">
        {/* Summary row */}
        <div className="physics-explain-summary">
          <div className="physics-explain-stat">
            <span className="physics-explain-stat-value">{Math.round(organResult.score)}</span>
            <span className="physics-explain-stat-label">Score</span>
          </div>
          <div className="physics-explain-stat">
            <span className="physics-explain-stat-value">{Math.round(organResult.coverage * 100)}%</span>
            <span className="physics-explain-stat-label">Coverage</span>
          </div>
          <div className="physics-explain-stat">
            <span className="physics-explain-stat-value">
              {presentWeight > 0 ? Math.round((presentWeight / totalWeight) * 100) : 0}%
            </span>
            <span className="physics-explain-stat-label">Confidence</span>
          </div>
        </div>

        {/* Contributions table */}
        <div className="physics-explain-table">
          <div className="physics-explain-table-header">
            <span>Metric</span>
            <span>Value</span>
            <span>Norm</span>
            <span>Weight</span>
            <span>Contrib</span>
          </div>
          {organResult.contributions.map((c) => (
            <div key={c.name} className={`physics-explain-table-row ${c.value == null ? 'missing' : ''}`}>
              <span className="physics-explain-metric-name">{c.name}</span>
              <span>{c.value != null ? `${c.value}` : '—'}</span>
              <span>{c.normalised != null ? c.normalised.toFixed(2) : '—'}</span>
              <span>{(c.weight * 100).toFixed(0)}%</span>
              <span>{c.weighted != null ? (c.weighted * 100).toFixed(1) : '—'}</span>
            </div>
          ))}
        </div>

        {/* Formula note */}
        <div className="physics-explain-note">
          <Info size={14} />
          <span>
            Score = Σ (weight<sub>i</sub> × normalised<sub>i</sub>) / Σ weight<sub>present</sub> × 100.
            Missing metrics are excluded — coverage reflects data completeness.
          </span>
        </div>
      </div>
    </div>
  );
};

export default ExplainabilityCard;
