/**
 * TrendsCard Component - API-Based Medical Trends Visualization
 * 
 * IMPORTANT: This component does NOT generate fake data.
 * It fetches real data from the backend API and updates ONLY when:
 * 1. User changes the selected metric
 * 2. User changes the time range (1D/1W/1M)
 * 3. WebSocket event signals new data (report uploaded)
 * 4. User manually refreshes
 * 
 * Like a stock chart - data changes only when underlying dataset changes.
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, Maximize2, X, AlertCircle, RefreshCw, BarChart2 } from 'lucide-react';
import { useTrends, type TrendDataPoint } from '../../hooks/useTrends';
import './TrendsCard.css';

interface TrendsCardProps {
  selectedMetric?: string;
  authToken?: string;
  apiBaseUrl?: string;
  refreshTrigger?: number; // Increment to trigger refetch (from WebSocket)
}

const metrics = [
  { key: 'index', label: 'Health Index', unit: '' },
  { key: 'glucose', label: 'Glucose', unit: 'mg/dL' },
  { key: 'bloodPressure', label: 'Blood Pressure', unit: 'mmHg' },
  { key: 'activity', label: 'Activity', unit: 'steps' },
];

function TrendsCard({
  selectedMetric: initialMetric = 'index',
  authToken,
  apiBaseUrl,
  refreshTrigger = 0,
}: TrendsCardProps) {
  const [selectedMetric, setSelectedMetric] = useState(initialMetric);
  const [timeRange, setTimeRange] = useState<'1D' | '1W' | '1M'>('1W');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Get auth token from localStorage if not provided
  const token = authToken || localStorage.getItem('access_token');

  // Use the API-based trends hook - NO fake data!
  const { data, stats, loading, error, refetch, lastFetchedAt } = useTrends(
    selectedMetric,
    timeRange,
    {
      authToken: token,
      apiBaseUrl,
    }
  );

  // Refetch when refreshTrigger changes (WebSocket event)
  useEffect(() => {
    if (refreshTrigger > 0) {
      refetch();
    }
  }, [refreshTrigger, refetch]);

  // Format chart data with proper date labels
  const chartData = data.map((point: TrendDataPoint, index: number) => {
    const date = new Date(point.timestamp);
    // Ensure numeric timestamp for XAxis
    const numericTimestamp = date.getTime();

    let dateLabel: string;
    if (timeRange === '1D') {
      dateLabel = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else if (timeRange === '1W') {
      dateLabel = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    } else {
      dateLabel = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }

    return {
      id: `${numericTimestamp}-${index}`, // Unique identifier
      time: numericTimestamp, // Numeric timestamp for XAxis
      value: point.value,
      flag: point.flag,
      dateLabel,
      fullDate: date.toLocaleString(),
    };
  });

  // Custom tooltip - reads directly from source data point
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    // Read from the original data point attached to the payload
    const dataPoint = payload[0]?.payload;
    if (!dataPoint) return null;

    const metricInfo = metrics.find(m => m.key === selectedMetric);
    // Use the value from the data point directly (same source as Area)
    const displayValue = dataPoint.value;

    return (
      <div className="trends-custom-tooltip">
        <div className="trends-tooltip-label">{dataPoint.fullDate}</div>
        <div className="trends-tooltip-value">
          {typeof displayValue === 'number' ? Math.round(displayValue * 10) / 10 : displayValue}
          {metricInfo?.unit && <span className="trends-tooltip-unit"> {metricInfo.unit}</span>}
        </div>
        {dataPoint.flag && dataPoint.flag !== 'Normal' && (
          <div className={`trends-tooltip-flag ${dataPoint.flag.toLowerCase()}`}>
            {dataPoint.flag}
          </div>
        )}
      </div>
    );
  };

  // Render the chart - shared between card and modal
  const renderChart = (height: number = 200) => {
    // Loading state
    if (loading) {
      return (
        <div className="trends-loading">
          <div className="trends-loading-spinner" />
          <span>Loading trends...</span>
        </div>
      );
    }

    // Error state
    if (error) {
      return (
        <div className="trends-error">
          <AlertCircle size={24} />
          <span>{error}</span>
          <button className="trends-retry-btn" onClick={refetch}>
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
      );
    }

    // Empty state
    if (chartData.length === 0) {
      return (
        <div className="trends-empty">
          <BarChart2 size={32} />
          <h4>No data available</h4>
          <p>Upload lab reports to see your {metrics.find(m => m.key === selectedMetric)?.label || 'health'} trends.</p>
        </div>
      );
    }

    // Determine chart color based on metric status
    const latestFlag = chartData[chartData.length - 1]?.flag;

    let strokeColor = '#10b981'; // Default green
    let fillId = 'colorNormal';

    if (latestFlag === 'High' || latestFlag === 'Critical') {
      strokeColor = '#ef4444'; // Red
      fillId = 'colorHigh';
    } else if (latestFlag === 'Low') {
      strokeColor = '#f59e0b'; // Amber
      fillId = 'colorLow';
    }

    return (
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorNormal" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorLow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--dash-border)" opacity={0.5} />
          <XAxis
            dataKey="time"
            type="number"
            scale="time"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(tick) => {
              const date = new Date(tick);
              if (timeRange === '1D') {
                return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
              } else if (timeRange === '1W') {
                return date.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric' });
              }
              return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            }}
            stroke="var(--dash-text-muted)"
            fontSize={11}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            stroke="var(--dash-text-muted)"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            width={40}
            domain={['auto', 'auto']}
          />
          <Tooltip content={<CustomTooltip />} isAnimationActive={false} />
          <Area
            type="monotone"
            dataKey="value"
            stroke={strokeColor}
            strokeWidth={2}
            fillOpacity={1}
            fill={`url(#${fillId})`}
            dot={false}
            activeDot={{ r: 6, strokeWidth: 2, fill: '#fff', stroke: strokeColor }}
          />
        </AreaChart>
      </ResponsiveContainer>
    );
  };

  return (
    <>
      <div className="trends-card">
        {/* Header */}
        <div className="trends-header">
          <div className="trends-title-row">
            <h3 className="trends-title">Medical Trends</h3>
            <div className="trends-header-actions">
              <button
                className="trends-expand-btn"
                onClick={() => setIsModalOpen(true)}
                title="Expand chart"
              >
                <Maximize2 size={16} />
              </button>
            </div>
          </div>

          {/* Controls Row */}
          <div className="trends-controls">
            {/* Metric Selector */}
            <div className="trends-metric-select">
              <select
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
                className="trends-select"
              >
                {metrics.map((m) => (
                  <option key={m.key} value={m.key}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Time Range */}
            <div className="trends-time-range">
              {(['1D', '1W', '1M'] as const).map((range) => (
                <button
                  key={range}
                  className={`trends-range-btn ${timeRange === range ? 'active' : ''}`}
                  onClick={() => setTimeRange(range)}
                >
                  {range}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Chart Section */}
        <div className="trends-chart-section">
          <div className="trends-chart-wrapper">
            {renderChart(200)}
          </div>
        </div>

        {/* Stats Summary */}
        {stats && (
          <div className="trends-stats">
            <div className="trends-stat-item">
              <span className="trends-stat-label">Current</span>
              <span className="trends-stat-value">{stats.current}</span>
              {stats.change !== 0 && !isNaN(stats.change) && isFinite(stats.change) && (
                <span className={`trends-stat-change ${stats.change > 0 ? 'positive' : 'negative'}`}>
                  {stats.change > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  {Math.abs(stats.change)}%
                </span>
              )}
              {(isNaN(stats.change) || !isFinite(stats.change)) && (
                <span className="trends-stat-change neutral">—</span>
              )}
            </div>
            <div className="trends-stat-item">
              <span className="trends-stat-label">Average</span>
              <span className="trends-stat-value">{isNaN(stats.avg) ? '—' : stats.avg}</span>
            </div>
            <div className="trends-stat-item">
              <span className="trends-stat-label">Min</span>
              <span className="trends-stat-value">{isNaN(stats.min) ? '—' : stats.min}</span>
            </div>
            <div className="trends-stat-item">
              <span className="trends-stat-label">Max</span>
              <span className="trends-stat-value">{isNaN(stats.max) ? '—' : stats.max}</span>
            </div>
          </div>
        )}

        {/* Last updated timestamp */}
        {lastFetchedAt && (
          <div className="trends-last-updated">
            Last updated: {lastFetchedAt.toLocaleTimeString()}
          </div>
        )}
      </div>

      {/* Expanded Modal */}
      <AnimatePresence>
        {isModalOpen && (
          <motion.div
            className="trends-modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsModalOpen(false)}
          >
            <motion.div
              className="trends-modal"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="trends-modal-header">
                <h3>Medical Trends - {metrics.find(m => m.key === selectedMetric)?.label}</h3>
                <button className="trends-modal-close" onClick={() => setIsModalOpen(false)}>
                  <X size={20} />
                </button>
              </div>

              <div className="trends-modal-controls">
                {/* Metric Selector */}
                <div className="trends-metric-select">
                  <select
                    value={selectedMetric}
                    onChange={(e) => setSelectedMetric(e.target.value)}
                    className="trends-select"
                  >
                    {metrics.map((m) => (
                      <option key={m.key} value={m.key}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Time Range */}
                <div className="trends-time-range">
                  {(['1D', '1W', '1M'] as const).map((range) => (
                    <button
                      key={range}
                      className={`trends-range-btn ${timeRange === range ? 'active' : ''}`}
                      onClick={() => setTimeRange(range)}
                    >
                      {range}
                    </button>
                  ))}
                </div>
              </div>

              <div className="trends-modal-chart">
                {renderChart(400)}
              </div>

              {/* Stats in modal */}
              {stats && (
                <div className="trends-stats trends-modal-stats">
                  <div className="trends-stat-item">
                    <span className="trends-stat-label">Current</span>
                    <span className="trends-stat-value">{stats.current}</span>
                    {stats.change !== 0 && !isNaN(stats.change) && isFinite(stats.change) && (
                      <span className={`trends-stat-change ${stats.change > 0 ? 'positive' : 'negative'}`}>
                        {stats.change > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                        {Math.abs(stats.change)}%
                      </span>
                    )}
                    {(isNaN(stats.change) || !isFinite(stats.change)) && (
                      <span className="trends-stat-change neutral">—</span>
                    )}
                  </div>
                  <div className="trends-stat-item">
                    <span className="trends-stat-label">Average</span>
                    <span className="trends-stat-value">{isNaN(stats.avg) ? '—' : stats.avg}</span>
                  </div>
                  <div className="trends-stat-item">
                    <span className="trends-stat-label">Minimum</span>
                    <span className="trends-stat-value">{isNaN(stats.min) ? '—' : stats.min}</span>
                  </div>
                  <div className="trends-stat-item">
                    <span className="trends-stat-label">Maximum</span>
                    <span className="trends-stat-value">{isNaN(stats.max) ? '—' : stats.max}</span>
                  </div>
                </div>
              )}

              <div className="trends-disclaimer">
                <AlertCircle size={14} />
                Not medical advice. For emergencies, contact a healthcare professional immediately.
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default TrendsCard;
