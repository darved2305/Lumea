/**
 * PhysicsTwin page – "Health Physics / Telemetry Twin".
 *
 * Layout mirrors Dashboard & Reports:
 *  - Same DashboardNavbar
 *  - Same card system, spacing, background
 *  - 2-column grid: left = 3D viewer (lazy-loaded), right = telemetry + explainability
 *
 * V2 upgrade: real-time SSE telemetry, conditions detection, body overlay,
 * recommendations, enhanced metrics/history tabs. NO layout changes.
 */

import { useState, useEffect, useCallback, useMemo, lazy, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText, Settings, RefreshCw, Activity, TrendingUp, TrendingDown,
  Minus, Radio, Wifi, WifiOff, AlertTriangle,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import DashboardNavbar from '../components/dashboard/DashboardNavbar';
import OrganTelemetryCard from '../components/physics/OrganTelemetryCard';
import ExplainabilityCard from '../components/physics/ExplainabilityCard';
import BodyImpactOverlay from '../components/physics/BodyImpactOverlay';
import YouTubeRecommendationsCard from '../components/physics/YouTubeRecommendationsCard';
import '../components/physics/YouTubeRecommendationsCard.css';
import {
  getLatestSnapshot,
  submitMetrics,
  getHistory,
  type PhysicsSnapshot,
  type OrganResult,
} from '../services/physicsApi';
import { useTelemetryStream } from '../hooks/useTelemetryStream';
import {
  detectConditions,
  getOrganSeverities,
  computeTrend,
  type TrendDirection,
} from '../services/conditionsEngine';
import type { DetectedConditionFE, Severity } from '../components/physics/BodyImpactOverlay';
import '../styles/dashboardTokens.css';
import '../styles/dashboardBase.css';
import './PhysicsTwin.css';

// Lazy-load the 3D viewer so initial bundle stays small
const TwinViewer = lazy(() => import('../components/physics/TwinViewer'));

const ORGAN_LABELS: Record<string, string> = {
  kidney: 'Kidney',
  heart: 'Heart',
  liver: 'Liver',
  lungs: 'Lungs',
  brain: 'Brain',
  blood: 'Blood',
};

// Demo metric sets users can submit to see the system in action
const DEMO_METRICS: Record<string, number> = {
  creatinine: 1.0, urea: 14, egfr: 95, sodium: 140, systolic_bp: 118,
  heart_rate: 72, diastolic_bp: 76, spo2: 97,
  alt: 25, ast: 22, bilirubin_total: 0.8,
  respiratory_rate: 16,
  stress_level: 2.5, sleep_hours: 7.5,
  glucose: 95, hemoglobin: 14.2,
};

// Key vital signs to show in the real-time metrics panel
const VITAL_SIGNS = [
  { key: 'heart_rate', label: 'Heart Rate', unit: 'bpm', icon: '♥' },
  { key: 'systolic_bp', label: 'Systolic BP', unit: 'mmHg', icon: '↑' },
  { key: 'diastolic_bp', label: 'Diastolic BP', unit: 'mmHg', icon: '↓' },
  { key: 'spo2', label: 'SpO₂', unit: '%', icon: '○' },
  { key: 'respiratory_rate', label: 'Resp Rate', unit: 'bpm', icon: '~' },
  { key: 'temperature', label: 'Temp', unit: '°F', icon: '◇' },
  { key: 'glucose', label: 'Glucose', unit: 'mg/dL', icon: '◆' },
  { key: 'stress_level', label: 'Stress', unit: 'score', icon: '⚡' },
];

// History chart metric options
const CHART_METRICS = [
  { key: 'heart_rate', label: 'Heart Rate', color: '#D4645C' },
  { key: 'systolic_bp', label: 'Systolic BP', color: '#6BAEDB' },
  { key: 'spo2', label: 'SpO₂', color: '#7AA874' },
  { key: 'respiratory_rate', label: 'Resp Rate', color: '#8B7EC8' },
  { key: 'glucose', label: 'Glucose', color: '#C4855C' },
  { key: 'stress_level', label: 'Stress', color: '#d4a843' },
];

type TabId = 'twin' | 'metrics' | 'history';

// ---------- Trend icon ----------
function TrendIcon({ direction }: { direction: TrendDirection }) {
  if (direction === 'up') return <TrendingUp size={12} className="trend-icon trend-up" />;
  if (direction === 'down') return <TrendingDown size={12} className="trend-icon trend-down" />;
  return <Minus size={12} className="trend-icon trend-stable" />;
}

function PhysicsTwin() {
  const navigate = useNavigate();

  // Auth
  const [userName, setUserName] = useState('User');
  const [healthStatus, setHealthStatus] = useState('');

  // Data
  const [snapshot, setSnapshot] = useState<PhysicsSnapshot | null>(null);
  const [history, setHistory] = useState<PhysicsSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // UI
  const [selectedOrgan, setSelectedOrgan] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('twin');
  const [chartMetric, setChartMetric] = useState('heart_rate');
  const [showOverlay, setShowOverlay] = useState(false);

  // Real-time telemetry stream
  const telemetry = useTelemetryStream(2000);

  // Conditions: detect from real-time telemetry
  const conditions: DetectedConditionFE[] = useMemo(() => {
    if (telemetry.current) {
      return detectConditions(telemetry.current.metrics);
    }
    if (snapshot) {
      return detectConditions(snapshot.raw_metrics);
    }
    return [];
  }, [telemetry.current, snapshot]);

  const organSeverities: Record<string, Severity> = useMemo(
    () => getOrganSeverities(conditions),
    [conditions],
  );

  // Trend arrows for each vital sign
  const trends: Record<string, TrendDirection> = useMemo(() => {
    const result: Record<string, TrendDirection> = {};
    for (const v of VITAL_SIGNS) {
      result[v.key] = computeTrend(telemetry.history, v.key);
    }
    return result;
  }, [telemetry.history]);

  // Chart data from telemetry history
  const chartData = useMemo(() => {
    return telemetry.history.slice(-60).map((r, i) => ({
      idx: i,
      time: new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      value: r.metrics[chartMetric] ?? 0,
    }));
  }, [telemetry.history, chartMetric]);

  // Fetch latest on mount — auto-computes from real user reports/profile data
  const bootstrap = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    if (!token) { navigate('/login'); return; }

    try {
      const meRes = await fetch(
        `${import.meta.env.VITE_API_URL?.replace(/\/+$/, '') || 'http://localhost:8000'}/api/me/bootstrap`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (meRes.status === 401) {
        localStorage.removeItem('access_token');
        navigate('/login');
        return;
      }
      if (meRes.ok) {
        const me = await meRes.json();
        setUserName(me.full_name?.split(' ')[0] || 'User');
        if (me.latest_health_index) setHealthStatus(`${Math.round(me.latest_health_index)}% Healthy`);
      }

      // GET /api/physics/latest now auto-computes from real Observation data
      const latest = await getLatestSnapshot();
      if (latest) {
        setSnapshot(latest);
        // Auto-select the first organ that has data if none selected
        if (!selectedOrgan && latest.organs) {
          const firstOrganWithData = Object.entries(latest.organs)
            .find(([, v]) => v.coverage > 0);
          if (firstOrganWithData) {
            setSelectedOrgan(firstOrganWithData[0]);
          }
        }
      }

      // Also pre-load history
      const hist = await getHistory(90);
      if (hist.length > 0) setHistory(hist);
    } catch (err) {
      console.error('Physics bootstrap error:', err);
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    window.scrollTo(0, 0);
    bootstrap();
  }, [bootstrap]);

  // Load history when tab switches
  useEffect(() => {
    if (activeTab === 'history') {
      getHistory(30).then(setHistory).catch(console.error);
    }
  }, [activeTab]);

  // Submit demo metrics
  const handleSubmitDemo = async () => {
    setSubmitting(true);
    try {
      const result = await submitMetrics(DEMO_METRICS);
      setSnapshot(result);
    } catch (err) {
      console.error('Submit error:', err);
    } finally {
      setSubmitting(false);
    }
  };

  // Organ selection
  const handleSelectOrgan = (id: string) => {
    setSelectedOrgan((prev) => (prev === id ? null : id));
  };

  // Merge 3D viewer scores with real-time data
  const organScores = useMemo(() => {
    if (snapshot) {
      return Object.fromEntries(
        Object.entries(snapshot.organs).map(([k, v]) => [k, { score: v.score, status: v.status }])
      );
    }
    return undefined;
  }, [snapshot]);

  const selectedResult: OrganResult | null = selectedOrgan && snapshot?.organs[selectedOrgan]
    ? snapshot.organs[selectedOrgan]
    : null;

  // Find worst performing organ for recommendations
  const worstOrgan = useMemo(() => {
    if (!snapshot?.organs) return null;
    
    let worst: { organ: string; score: number; result: OrganResult } | null = null;
    
    for (const [organKey, organData] of Object.entries(snapshot.organs)) {
      // Skip if score is 100 (perfect health)
      if (organData.score >= 100) continue;
      
      if (!worst || organData.score < worst.score) {
        worst = { organ: organKey, score: organData.score, result: organData };
      }
    }
    
    return worst;
  }, [snapshot]);

  // Auto-select worst organ if nothing selected
  useEffect(() => {
    if (!selectedOrgan && worstOrgan) {
      setSelectedOrgan(worstOrgan.organ);
    }
  }, [worstOrgan, selectedOrgan]);

  // Current metric value from telemetry
  const currentMetrics = telemetry.current?.metrics ?? snapshot?.raw_metrics ?? {};

  const tabs: { id: TabId; label: string }[] = [
    { id: 'twin', label: 'Twin View' },
    { id: 'metrics', label: 'Metrics' },
    { id: 'history', label: 'History' },
  ];

  // Loading
  if (loading) {
    return (
      <div className="dashboard-page">
        <DashboardNavbar userName="Loading..." userStatus="" />
        <div className="dashboard-content">
          <div className="dashboard-container">
            <div className="physics-loading">
              <div className="loading-spinner" />
              <p>Loading Physics Twin...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-page">
      {/* Background (same as dashboard) */}
      <div className="dashboard-background">
        <div className="dashboard-bg-blob dashboard-bg-blob-1" />
        <div className="dashboard-bg-blob dashboard-bg-blob-2" />
      </div>

      <DashboardNavbar userName={userName} userStatus={healthStatus} />

      <div className="dashboard-content">
        <div className="dashboard-container">
          {/* Header */}
          <motion.div
            className="physics-header"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
          >
            <div className="physics-header-left">
              <h1>Physics Twin</h1>
              <p>Your digital health telemetry and organ scoring</p>
              {/* Connection status */}
              <div className="physics-connection-status">
                {telemetry.connected ? (
                  <span className="physics-conn-badge physics-conn-live">
                    <Radio size={12} className="physics-conn-pulse" />
                    Live
                  </span>
                ) : telemetry.simulated ? (
                  <span className="physics-conn-badge physics-conn-sim">
                    <Wifi size={12} />
                    Simulated
                  </span>
                ) : (
                  <span className="physics-conn-badge physics-conn-off">
                    <WifiOff size={12} />
                    Offline
                  </span>
                )}
                {telemetry.staleness > 5 && (
                  <span className="physics-stale-badge">
                    {telemetry.staleness}s ago
                  </span>
                )}
              </div>
            </div>
            <div className="physics-header-actions">
              <button
                className={`dash-btn ${showOverlay ? 'dash-btn-primary' : 'dash-btn-secondary'}`}
                onClick={() => setShowOverlay(!showOverlay)}
              >
                <Activity size={16} />
                Impact View
              </button>
              <button className="dash-btn dash-btn-secondary">
                <FileText size={16} />
                Documentation
              </button>
              <button className="dash-btn dash-btn-secondary">
                <Settings size={16} />
                Setup Details
              </button>
            </div>
          </motion.div>

          {/* Conditions banner */}
          <AnimatePresence>
            {conditions.length > 0 && (
              <motion.div
                className="physics-conditions-banner"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <AlertTriangle size={16} />
                <span>
                  <strong>{conditions.length} condition{conditions.length > 1 ? 's' : ''}</strong> detected from real-time telemetry
                </span>
                <div className="physics-conditions-pills">
                  {conditions.map((c) => (
                    <span key={c.id} className={`physics-condition-pill physics-cond-${c.severity}`}>
                      {c.name}
                    </span>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Main grid */}
          <div className="physics-main-grid">
            {/* LEFT: Twin viewer */}
            <motion.div
              className="physics-left-col"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.1 }}
            >
              <div className="dash-card physics-twin-card">
                {/* Tabs */}
                <div className="physics-tabs">
                  {tabs.map((tab) => (
                    <button
                      key={tab.id}
                      className={`physics-tab ${activeTab === tab.id ? 'active' : ''}`}
                      onClick={() => setActiveTab(tab.id)}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Tab content */}
                <div className="physics-tab-content">
                  {activeTab === 'twin' && (
                    <div className="physics-viewer-wrapper">
                      {showOverlay ? (
                        <div className="physics-overlay-container">
                          <BodyImpactOverlay
                            conditions={conditions}
                            organSeverities={organSeverities}
                            selectedOrgan={selectedOrgan}
                            onSelectOrgan={handleSelectOrgan}
                          />
                        </div>
                      ) : (
                        <Suspense fallback={
                          <div className="physics-viewer-loading">
                            <div className="loading-spinner" />
                            <p>Loading 3D viewer...</p>
                          </div>
                        }>
                          <TwinViewer
                            selectedOrgan={selectedOrgan}
                            onSelectOrgan={handleSelectOrgan}
                            organScores={organScores}
                          />
                        </Suspense>
                      )}

                      {!snapshot && !telemetry.current && (
                        <div className="physics-no-data-overlay">
                          <p>No health data found — upload a report to see your Physics Twin</p>
                          <button
                            className="dash-btn dash-btn-primary"
                            onClick={handleSubmitDemo}
                            disabled={submitting}
                          >
                            {submitting ? (
                              <><RefreshCw size={16} className="spinning" /> Computing...</>
                            ) : (
                              'Load Demo Data'
                            )}
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'metrics' && (
                    <div className="physics-metrics-tab">
                      <div className="physics-metrics-header">
                        <h3>Real-Time Vitals</h3>
                        <div className="physics-metrics-header-right">
                          <button
                            className="dash-btn dash-btn-primary"
                            onClick={handleSubmitDemo}
                            disabled={submitting}
                          >
                            {submitting ? (
                              <><RefreshCw size={16} className="spinning" /> Submitting...</>
                            ) : (
                              <><RefreshCw size={16} /> Score Metrics</>
                            )}
                          </button>
                        </div>
                      </div>

                      {/* Vital signs grid with trend arrows */}
                      <div className="physics-vitals-grid">
                        {VITAL_SIGNS.map((v) => {
                          const value = currentMetrics[v.key];
                          const trend = trends[v.key];
                          return (
                            <motion.div
                              key={v.key}
                              className="physics-vital-card"
                              initial={{ opacity: 0, scale: 0.95 }}
                              animate={{ opacity: 1, scale: 1 }}
                              transition={{ duration: 0.3 }}
                            >
                              <div className="physics-vital-header">
                                <span className="physics-vital-icon">{v.icon}</span>
                                <span className="physics-vital-label">{v.label}</span>
                                <TrendIcon direction={trend} />
                              </div>
                              <div className="physics-vital-value">
                                {value != null ? (
                                  <>
                                    <span className="physics-vital-number">
                                      {typeof value === 'number' ? value.toFixed(1) : value}
                                    </span>
                                    <span className="physics-vital-unit">{v.unit}</span>
                                  </>
                                ) : (
                                  <span className="physics-vital-na">—</span>
                                )}
                              </div>
                            </motion.div>
                          );
                        })}
                      </div>

                      {/* All metrics in chips */}
                      {(telemetry.current || snapshot) && (
                        <>
                          <h4 className="physics-metrics-subtitle">All Data Points</h4>
                          <div className="physics-metrics-grid">
                            {Object.entries(currentMetrics).map(([key, val]) => (
                              <div key={key} className="physics-metric-chip">
                                <span className="physics-metric-chip-name">{key.replace(/_/g, ' ')}</span>
                                <span className="physics-metric-chip-value">
                                  {typeof val === 'number' ? val.toFixed(1) : val}
                                </span>
                              </div>
                            ))}
                          </div>
                        </>
                      )}

                      {!telemetry.current && !snapshot && (
                        <p className="physics-hint">Submit metrics to see data here</p>
                      )}
                    </div>
                  )}

                  {activeTab === 'history' && (
                    <div className="physics-history-tab">
                      {/* Real-time chart */}
                      <div className="physics-chart-section">
                        <div className="physics-chart-header">
                          <h3>Live Telemetry</h3>
                          <div className="physics-chart-selector">
                            {CHART_METRICS.map((m) => (
                              <button
                                key={m.key}
                                className={`physics-chart-btn ${chartMetric === m.key ? 'active' : ''}`}
                                onClick={() => setChartMetric(m.key)}
                              >
                                {m.label}
                              </button>
                            ))}
                          </div>
                        </div>
                        {chartData.length > 2 ? (
                          <div className="physics-chart-container">
                            <ResponsiveContainer width="100%" height={250}>
                              <LineChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--dash-border-light)" />
                                <XAxis
                                  dataKey="time"
                                  tick={{ fontSize: 10, fill: 'var(--dash-text-muted)' }}
                                  interval="preserveStartEnd"
                                />
                                <YAxis
                                  tick={{ fontSize: 10, fill: 'var(--dash-text-muted)' }}
                                  domain={['auto', 'auto']}
                                />
                                <Tooltip
                                  contentStyle={{
                                    background: 'var(--dash-surface)',
                                    border: '1px solid var(--dash-border-light)',
                                    borderRadius: '8px',
                                    fontSize: '12px',
                                  }}
                                />
                                <Line
                                  type="monotone"
                                  dataKey="value"
                                  stroke={CHART_METRICS.find((m) => m.key === chartMetric)?.color || '#6b9175'}
                                  strokeWidth={2}
                                  dot={false}
                                  animationDuration={300}
                                />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        ) : (
                          <p className="physics-hint">Collecting telemetry data... chart will appear shortly.</p>
                        )}
                      </div>

                      {/* Historical snapshots */}
                      <div className="physics-snapshots-section">
                        <h3>Scored Snapshots</h3>
                        {history.length > 0 ? (
                          <div className="physics-history-list">
                            {history.slice().reverse().map((snap) => (
                              <div key={snap.id} className="physics-history-row">
                                <span className="physics-history-time">
                                  {new Date(snap.timestamp).toLocaleString()}
                                </span>
                                <span className={`dash-badge dash-badge-${snap.overall_status === 'Healthy' ? 'success' : snap.overall_status === 'Watch' ? 'warning' : 'danger'}`}>
                                  {snap.overall_score.toFixed(1)}
                                </span>
                                <span className="physics-history-status">{snap.overall_status}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="physics-hint">No history available yet. Submit metrics to build up history.</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>

            {/* RIGHT: Telemetry + Explainability + Recommendations */}
            <motion.div
              className="physics-right-col"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.2 }}
            >
              <OrganTelemetryCard
                overallScore={snapshot?.overall_score ?? 0}
                overallStatus={snapshot?.overall_status ?? 'Risk'}
                selectedOrgan={selectedOrgan}
                organResult={selectedResult}
                lastUpdated={telemetry.current?.timestamp ?? snapshot?.timestamp ?? null}
              />
            </motion.div>
          </div>

          {/* Full-width two-column layout: YouTube (left) + Explainability (right) */}
          <div className="physics-cards-row">
            <div className="physics-cards-row-item">
              <YouTubeRecommendationsCard
                selectedOrgan={selectedOrgan}
                organResult={selectedResult}
                currentMetrics={currentMetrics}
              />
            </div>
            <div className="physics-cards-row-item">
              <ExplainabilityCard
                selectedOrgan={selectedOrgan}
                organResult={selectedResult}
                organLabel={selectedOrgan ? (ORGAN_LABELS[selectedOrgan] || selectedOrgan) : ''}
              />
            </div>
          </div>

          {/* Data quality disclaimer */}
          <div className="physics-disclaimer">
            <AlertTriangle size={14} />
            <span>
              Scores are computed from your uploaded health reports and profile data.
              Real-time telemetry values are simulated for visualization purposes.
              Not intended for medical diagnosis. Always consult a healthcare professional.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PhysicsTwin;
