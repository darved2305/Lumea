/**
 * BodyImpactOverlay – 2D SVG body silhouette with animated organ glow zones.
 *
 * Overlays on top of the 3D viewer to show condition-aware highlighting.
 * Male / female toggle. Each organ zone pulses based on severity.
 */

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// ---------- Types ----------

export type Severity = 'mild' | 'moderate' | 'severe';

export interface DetectedConditionFE {
  id: string;
  name: string;
  description: string;
  severity: Severity;
  affected_organs: string[];
  trigger_metrics: Record<string, number>;
  recommendations: string[];
  youtube_queries: string[];
}

interface BodyImpactOverlayProps {
  conditions: DetectedConditionFE[];
  organSeverities: Record<string, Severity>;
  selectedOrgan: string | null;
  onSelectOrgan: (id: string) => void;
}

// ---------- Severity colors ----------

const SEVERITY_COLORS: Record<Severity, { fill: string; glow: string }> = {
  mild:     { fill: 'rgba(212, 168, 67, 0.35)',  glow: 'rgba(212, 168, 67, 0.6)' },
  moderate: { fill: 'rgba(230, 140, 60, 0.4)',   glow: 'rgba(230, 140, 60, 0.7)' },
  severe:   { fill: 'rgba(196, 100, 92, 0.5)',   glow: 'rgba(196, 100, 92, 0.8)' },
};

const HEALTHY_COLOR = { fill: 'rgba(107, 145, 117, 0.2)', glow: 'rgba(107, 145, 117, 0.4)' };

// ---------- Organ zone positions on SVG (viewBox 0 0 200 400) ----------

interface OrganZone {
  id: string;
  label: string;
  cx: number;
  cy: number;
  rx: number;
  ry: number;
}

const ORGAN_ZONES: OrganZone[] = [
  { id: 'brain',  label: 'Brain',  cx: 100, cy: 38,  rx: 22, ry: 18 },
  { id: 'heart',  label: 'Heart',  cx: 110, cy: 140, rx: 16, ry: 18 },
  { id: 'lungs',  label: 'Lungs',  cx: 88,  cy: 135, rx: 24, ry: 25 },
  { id: 'liver',  label: 'Liver',  cx: 118, cy: 175, rx: 18, ry: 14 },
  { id: 'kidney', label: 'Kidney', cx: 82,  cy: 190, rx: 14, ry: 12 },
  { id: 'blood',  label: 'Blood',  cx: 100, cy: 158, rx: 12, ry: 12 },
];

// ---------- SVG body silhouette path ----------

const BODY_PATH_MALE = `
  M100,15 
  C115,15 125,25 125,40 C125,55 115,65 100,70 C85,65 75,55 75,40 C75,25 85,15 100,15 Z
  M100,70 L100,75 
  M88,80 C75,85 65,95 62,120 L60,150 L62,170 C62,175 65,180 70,185 L75,190 L72,220 
  L70,260 L68,310 L72,340 L65,370 L68,385 L80,390 L82,385 L78,370 L82,340 L88,310 
  L92,260 L95,220 L100,198 L105,220 L108,260 L112,310 L118,340 L122,370 L118,385 
  L120,390 L135,385 L132,370 L128,340 L130,310 L128,260 L125,220 L125,190 L130,185 
  C135,180 138,175 138,170 L140,150 L138,120 C135,95 125,85 112,80 L100,75 Z
`;

const BODY_PATH_FEMALE = `
  M100,15 
  C115,15 125,25 125,40 C125,55 115,65 100,70 C85,65 75,55 75,40 C75,25 85,15 100,15 Z
  M100,70 L100,75 
  M88,80 C72,86 62,98 60,120 L57,150 L58,168 C58,174 60,180 64,186
  L70,195 L66,225 L64,260 L62,310 L66,340 L60,370 L63,385 L76,390 L78,385 L74,370 
  L78,340 L84,310 L88,260 L92,225 L95,198 L100,192 L105,198 L108,225 L112,260 
  L116,310 L122,340 L126,370 L122,385 L124,390 L137,385 L140,370 L134,340 L138,310 
  L136,260 L134,225 L130,195 L136,186 C140,180 142,174 142,168 L143,150 L140,120 
  C138,98 128,86 112,80 L100,75 Z
`;

// ---------- Animated organ zone ----------

interface OrganZoneCircleProps {
  zone: OrganZone;
  severity: Severity | null;
  isSelected: boolean;
  onClick: () => void;
}

function OrganZoneCircle({ zone, severity, isSelected, onClick }: OrganZoneCircleProps) {
  const colors = severity ? SEVERITY_COLORS[severity] : HEALTHY_COLOR;
  const pulseSpeed = severity === 'severe' ? 0.8 : severity === 'moderate' ? 1.2 : 1.8;

  return (
    <g onClick={onClick} style={{ cursor: 'pointer' }}>
      {/* Outer glow */}
      <motion.ellipse
        cx={zone.cx}
        cy={zone.cy}
        rx={zone.rx + 4}
        ry={zone.ry + 4}
        fill="none"
        stroke={colors.glow}
        strokeWidth={isSelected ? 2.5 : 1.5}
        initial={{ opacity: 0.3 }}
        animate={{
          opacity: severity ? [0.2, 0.7, 0.2] : isSelected ? 0.6 : 0.2,
          scale: severity ? [1, 1.08, 1] : 1,
        }}
        transition={{
          duration: pulseSpeed,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        style={{ transformOrigin: `${zone.cx}px ${zone.cy}px` }}
      />

      {/* Inner fill */}
      <motion.ellipse
        cx={zone.cx}
        cy={zone.cy}
        rx={zone.rx}
        ry={zone.ry}
        fill={colors.fill}
        stroke={isSelected ? 'rgba(107, 145, 117, 0.8)' : 'transparent'}
        strokeWidth={isSelected ? 2 : 0}
        whileHover={{ scale: 1.1, opacity: 0.8 }}
        style={{ transformOrigin: `${zone.cx}px ${zone.cy}px` }}
      />

      {/* Label */}
      {isSelected && (
        <motion.text
          x={zone.cx}
          y={zone.cy - zone.ry - 6}
          textAnchor="middle"
          fill="#2d3e2f"
          fontSize="8"
          fontWeight="600"
          fontFamily="DM Sans, sans-serif"
          initial={{ opacity: 0, y: 3 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {zone.label}
        </motion.text>
      )}
    </g>
  );
}

// ---------- Main component ----------

const BodyImpactOverlay: React.FC<BodyImpactOverlayProps> = ({
  conditions,
  organSeverities,
  selectedOrgan,
  onSelectOrgan,
}) => {
  const [gender, setGender] = useState<'male' | 'female'>('male');

  const activeConditionCount = conditions.length;
  const worstSeverity = useMemo(() => {
    if (conditions.length === 0) return null;
    const rank: Record<Severity, number> = { mild: 1, moderate: 2, severe: 3 };
    let worst: Severity = 'mild';
    for (const c of conditions) {
      if (rank[c.severity] > rank[worst]) worst = c.severity;
    }
    return worst;
  }, [conditions]);

  return (
    <div className="body-impact-overlay">
      {/* Gender toggle */}
      <div className="body-impact-toggle">
        <button
          className={`body-impact-toggle-btn ${gender === 'male' ? 'active' : ''}`}
          onClick={() => setGender('male')}
        >
          Male
        </button>
        <button
          className={`body-impact-toggle-btn ${gender === 'female' ? 'active' : ''}`}
          onClick={() => setGender('female')}
        >
          Female
        </button>
      </div>

      {/* SVG body */}
      <svg
        viewBox="0 0 200 400"
        className="body-impact-svg"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <filter id="bodyGlow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <linearGradient id="bodyGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e8ddd0" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#d5cfc5" stopOpacity="0.3" />
          </linearGradient>
        </defs>

        {/* Body silhouette */}
        <path
          d={gender === 'male' ? BODY_PATH_MALE : BODY_PATH_FEMALE}
          fill="url(#bodyGradient)"
          stroke="#c5bfb5"
          strokeWidth="1"
          strokeLinejoin="round"
        />

        {/* Organ zones */}
        {ORGAN_ZONES.map((zone) => (
          <OrganZoneCircle
            key={zone.id}
            zone={zone}
            severity={organSeverities[zone.id] || null}
            isSelected={selectedOrgan === zone.id}
            onClick={() => onSelectOrgan(zone.id)}
          />
        ))}
      </svg>

      {/* Status indicator */}
      <AnimatePresence>
        {activeConditionCount > 0 && (
          <motion.div
            className={`body-impact-status body-impact-status-${worstSeverity}`}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
          >
            <span className="body-impact-status-dot" />
            {activeConditionCount} condition{activeConditionCount > 1 ? 's' : ''} detected
          </motion.div>
        )}
      </AnimatePresence>

      {!activeConditionCount && (
        <div className="body-impact-status body-impact-status-healthy">
          <span className="body-impact-status-dot" />
          All clear – no conditions detected
        </div>
      )}
    </div>
  );
};

export default BodyImpactOverlay;
