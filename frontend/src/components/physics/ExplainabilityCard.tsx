/**
 * ExplainabilityCard – deterministic scoring breakdown.
 * Shows weights, normalised contributions, coverage/confidence.
 * Matches clean Tailwind design system.
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
      <div className="dash-card h-full flex flex-col">
        <div className="dash-card-header">
          <h3 className="dash-card-title flex items-center gap-2">
            <BarChart3 size={18} />
            Why this score?
          </h3>
        </div>
        <div className="dash-card-body flex-1 flex items-center justify-center">
          <div className="text-center" style={{ color: 'var(--dash-text-muted)' }}>
            <Info size={48} style={{ margin: '0 auto', opacity: 0.3 }} />
            <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>Select an organ to see details</p>
          </div>
        </div>
      </div>
    );
  }

  const presentMetrics = organResult.contributions.filter((c) => c.value != null);
  const totalWeight = organResult.contributions.reduce((s, c) => s + c.weight, 0);
  const presentWeight = presentMetrics.reduce((s, c) => s + c.weight, 0);
  const confidence = presentWeight > 0 ? Math.round((presentWeight / totalWeight) * 100) : 0;

  return (
    <div className="dash-card h-full flex flex-col">
      {/* Header */}
      <div className="dash-card-header">
        <h3 className="dash-card-title flex items-center gap-2">
          <BarChart3 size={18} />
          Why this score?
        </h3>
        <span className={`dash-badge dash-badge-${organResult.status === 'Healthy' ? 'success' : organResult.status === 'Watch' ? 'warning' : 'danger'}`}>
          {organLabel}
        </span>
      </div>

      {/* Content */}
      <div className="dash-card-body flex-1" style={{ maxHeight: '500px', overflowY: 'auto' }}>
        {/* Summary Stats */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '1rem',
          marginBottom: '1.5rem',
          padding: '1rem',
          background: 'var(--dash-accent-pale)',
          borderRadius: 'var(--dash-radius-lg)',
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--dash-success)' }}>
              {Math.round(organResult.score)}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--dash-text-muted)', marginTop: '0.25rem' }}>Score</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--dash-info)' }}>
              {Math.round(organResult.coverage * 100)}%
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--dash-text-muted)', marginTop: '0.25rem' }}>Coverage</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--dash-accent)' }}>
              {confidence}%
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--dash-text-muted)', marginTop: '0.25rem' }}>Confidence</div>
          </div>
        </div>

        {/* Metrics Table */}
        <div style={{ marginTop: '1rem' }}>
          {/* Header */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr',
            gap: '0.5rem',
            padding: '0.5rem 0.75rem',
            fontSize: '0.75rem',
            fontWeight: 600,
            color: 'var(--dash-text-muted)',
            textTransform: 'uppercase',
            borderBottom: '2px solid var(--dash-border)',
          }}>
            <span>Metric</span>
            <span style={{ textAlign: 'right' }}>Value</span>
            <span style={{ textAlign: 'right' }}>Norm</span>
            <span style={{ textAlign: 'right' }}>Weight</span>
            <span style={{ textAlign: 'right' }}>Contrib</span>
          </div>

          {/* Rows */}
          {organResult.contributions.map((c, index) => (
            <div
              key={c.name}
              style={{
                display: 'grid',
                gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr',
                gap: '0.5rem',
                padding: '0.625rem 0.75rem',
                fontSize: '0.875rem',
                background: c.value == null ? 'transparent' : (index % 2 === 0 ? 'var(--dash-surface)' : 'var(--dash-surface-hover)'),
                borderRadius: 'var(--dash-radius-sm)',
                color: c.value == null ? 'var(--dash-text-muted)' : 'var(--dash-text)',
                transition: 'background 0.2s',
              }}
              onMouseEnter={(e) => {
                if (c.value != null) e.currentTarget.style.background = 'var(--dash-accent-pale)';
              }}
              onMouseLeave={(e) => {
                if (c.value != null) e.currentTarget.style.background = index % 2 === 0 ? 'var(--dash-surface)' : 'var(--dash-surface-hover)';
              }}
            >
              <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {c.name}
              </span>
              <span style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                {c.value != null ? c.value.toString() : '—'}
              </span>
              <span style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                {c.normalised != null ? c.normalised.toFixed(2) : '—'}
              </span>
              <span style={{ textAlign: 'right', fontWeight: 600, color: 'var(--dash-info)' }}>
                {(c.weight * 100).toFixed(0)}%
              </span>
              <span style={{ textAlign: 'right', fontWeight: 600, color: 'var(--dash-success)' }}>
                {c.weighted != null ? (c.weighted * 100).toFixed(1) : '—'}
              </span>
            </div>
          ))}
        </div>

        {/* Formula Note */}
        <div style={{
          marginTop: '1.5rem',
          padding: '1rem',
          background: 'var(--dash-accent-pale)',
          border: '1px solid var(--dash-accent-light)',
          borderRadius: 'var(--dash-radius-lg)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.75rem',
        }}>
          <Info size={16} style={{ color: 'var(--dash-accent)', flexShrink: 0, marginTop: '2px' }} />
          <p style={{ fontSize: '0.75rem', color: 'var(--dash-text-secondary)', lineHeight: 1.6 }}>
            <strong>Score Formula:</strong> Σ (weight<sub>i</sub> × normalised<sub>i</sub>) / Σ weight<sub>present</sub> × 100.
            Missing metrics are excluded — coverage reflects data completeness.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ExplainabilityCard;
