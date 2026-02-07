/**
 * OrganTelemetryCard – shows overall score, status badge, and selected organ detail.
 * Styled to match the "Health Profile Complete" card from Reports page.
 */

import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Heart, Droplets, Brain, Wind, Stethoscope } from 'lucide-react';
import type { OrganResult } from '../../services/physicsApi';

const ORGAN_ICONS: Record<string, React.ReactNode> = {
  kidney: <Droplets size={18} />,
  heart: <Heart size={18} />,
  liver: <Activity size={18} />,
  lungs: <Wind size={18} />,
  brain: <Brain size={18} />,
  blood: <Droplets size={18} />,
};

const ORGAN_LABELS: Record<string, string> = {
  kidney: 'Kidney',
  heart: 'Heart',
  liver: 'Liver',
  lungs: 'Lungs',
  brain: 'Brain',
  blood: 'Blood',
};

interface OrganTelemetryCardProps {
  overallScore: number;
  overallStatus: string;
  selectedOrgan: string | null;
  organResult: OrganResult | null;
  lastUpdated: string | null;
}

// Animated counter
function AnimatedNumber({ value, decimals = 1 }: { value: number; decimals?: number }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef<number | null>(null);

  useEffect(() => {
    const start = display;
    const diff = value - start;
    const duration = 800;
    const startTime = performance.now();

    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(start + diff * eased);
      if (progress < 1) {
        ref.current = requestAnimationFrame(animate);
      }
    };

    ref.current = requestAnimationFrame(animate);
    return () => { if (ref.current) cancelAnimationFrame(ref.current); };
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps

  return <>{display.toFixed(decimals)}</>;
}

const OrganTelemetryCard: React.FC<OrganTelemetryCardProps> = ({
  overallScore,
  overallStatus,
  selectedOrgan,
  organResult,
  lastUpdated,
}) => {
  const statusClass = overallStatus === 'Healthy' ? 'success' : overallStatus === 'Watch' ? 'warning' : 'danger';

  return (
    <div className="dash-card physics-telemetry-card">
      <div className="dash-card-header">
        <h3 className="dash-card-title">
          <Stethoscope size={18} />
          Organ Telemetry
        </h3>
        <span className={`dash-badge dash-badge-${statusClass}`}>
          {overallStatus}
        </span>
      </div>

      <div className="dash-card-body">
        {/* Overall score */}
        <div className="physics-score-big">
          <span className="physics-score-number">
            <AnimatedNumber value={overallScore} />
          </span>
          <span className="physics-score-label">Overall Health Score</span>
        </div>

        {/* Selected organ detail */}
        <AnimatePresence mode="wait">
          {selectedOrgan && organResult && (
            <motion.div
              key={selectedOrgan}
              className="physics-organ-detail"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
            >
              <div className="physics-organ-detail-header">
                {ORGAN_ICONS[selectedOrgan] || <Activity size={18} />}
                <span>{ORGAN_LABELS[selectedOrgan] || selectedOrgan}</span>
                <span className={`dash-badge dash-badge-${organResult.status === 'Healthy' ? 'success' : organResult.status === 'Watch' ? 'warning' : 'danger'}`}>
                  {Math.round(organResult.score)}%
                </span>
              </div>

              <div className="physics-organ-metrics">
                {organResult.contributions.map((c) => (
                  <div key={c.name} className="physics-metric-row">
                    <span className="physics-metric-name">{c.name}</span>
                    <span className="physics-metric-value">
                      {c.value != null ? `${c.value} ${c.unit}` : '—'}
                    </span>
                    <div className="physics-metric-bar-track">
                      <motion.div
                        className="physics-metric-bar-fill"
                        initial={{ width: 0 }}
                        animate={{ width: c.normalised != null ? `${c.normalised * 100}%` : '0%' }}
                        transition={{ duration: 0.6, ease: 'easeOut' }}
                        style={{
                          backgroundColor: c.normalised != null
                            ? c.normalised >= 0.75 ? 'var(--dash-success)' : c.normalised >= 0.5 ? 'var(--dash-warning)' : 'var(--dash-danger)'
                            : 'var(--dash-border)',
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="physics-organ-coverage">
                Coverage: {Math.round(organResult.coverage * 100)}%
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {!selectedOrgan && (
          <p className="physics-hint">Select an organ on the 3D model to view details</p>
        )}

        {lastUpdated && (
          <div className="physics-last-updated">
            Last updated: {new Date(lastUpdated).toLocaleString()}
          </div>
        )}
      </div>
    </div>
  );
};

export default OrganTelemetryCard;
