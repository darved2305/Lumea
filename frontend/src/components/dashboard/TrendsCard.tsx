import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, Maximize2, X, AlertCircle, Play, Pause } from 'lucide-react';
import { useLiveSeries } from '../../hooks/useDashboard';
import './TrendsCard.css';

interface TrendsCardProps {
  selectedMetric?: string;
}

const metrics = [
  { key: 'index', label: 'Health Index' },
  { key: 'sleep', label: 'Sleep' },
  { key: 'bloodPressure', label: 'Blood Pressure' },
  { key: 'glucose', label: 'Glucose' },
  { key: 'activity', label: 'Activity' },
];

function TrendsCard({ selectedMetric: initialMetric = 'index' }: TrendsCardProps) {
  const [selectedMetric, setSelectedMetric] = useState(initialMetric);
  const [timeRange, setTimeRange] = useState<'1D' | '1W' | '1M'>('1D');
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  const { data, isLive, toggleLive } = useLiveSeries(selectedMetric, timeRange);

  // Calculate stats from data
  const calculateStats = () => {
    if (data.length === 0) return { current: 0, avg: 0, min: 0, max: 0, change: 0 };

    const values = data.map(d => d.value);
    const current = values[values.length - 1];
    const previous = values[values.length - 2] || current;
    const avg = values.reduce((sum, v) => sum + v, 0) / values.length;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const change = ((current - previous) / previous) * 100;

    return {
      current: Math.round(current * 10) / 10,
      avg: Math.round(avg * 10) / 10,
      min: Math.round(min * 10) / 10,
      max: Math.round(max * 10) / 10,
      change: Math.round(change * 10) / 10,
    };
  };

  const stats = calculateStats();

  // Format chart data
  const chartData = data.map((point) => ({
    timestamp: point.timestamp,
    value: point.value,
    date: new Date(point.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }),
  }));

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="trends-custom-tooltip">
          <div className="trends-tooltip-label">
            {new Date(payload[0].payload.timestamp).toLocaleString('en-US', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
          <div className="trends-tooltip-value">
            {Math.round(payload[0].value * 10) / 10}
          </div>
        </div>
      );
    }
    return null;
  };

  const renderChart = (height: number = 320) => (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6b9175" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#6b9175" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5dfd5" opacity={0.5} />
        <XAxis
          dataKey="date"
          stroke="#999999"
          fontSize={12}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          stroke="#999999"
          fontSize={12}
          tickLine={false}
          domain={[40, 100]}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="value"
          stroke="#4a7c59"
          strokeWidth={3}
          fill="url(#colorValue)"
          animationDuration={300}
        />
      </AreaChart>
    </ResponsiveContainer>
  );

  const renderContent = () => (
    <>
      <div className="dash-card-header trends-card-header">
        <div className="trends-header-left">
          <div className="trends-title-group">
            <h2 className="dash-card-title">Medical Trends</h2>
            <span className="trends-subtitle">Real-time health metrics visualization</span>
          </div>
        </div>

        <div className="trends-header-right">
          {/* Metric Selector */}
          <div className="trends-metrics">
            {metrics.map((metric) => (
              <motion.button
                key={metric.key}
                className={`trends-metric-chip ${selectedMetric === metric.key ? 'active' : ''}`}
                onClick={() => setSelectedMetric(metric.key)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {metric.label}
              </motion.button>
            ))}
          </div>

          {/* Time Range */}
          <div className="trends-time-range">
            {(['1D', '1W', '1M'] as const).map((range) => (
              <button
                key={range}
                className={`trends-time-btn ${timeRange === range ? 'active' : ''}`}
                onClick={() => setTimeRange(range)}
              >
                {range}
              </button>
            ))}
          </div>

          {/* Live Toggle */}
          {timeRange === '1D' && (
            <button
              className={`trends-live-indicator ${!isLive ? 'paused' : ''}`}
              onClick={toggleLive}
              title={isLive ? 'Pause live updates' : 'Resume live updates'}
            >
              <div className="trends-live-dot" />
              {isLive ? (
                <>
                  LIVE
                  <Pause size={12} />
                </>
              ) : (
                <>
                  PAUSED
                  <Play size={12} />
                </>
              )}
            </button>
          )}
        </div>
      </div>

      <div className="trends-chart-section">
        <div className="trends-chart-wrapper">
          {chartData.length > 0 ? (
            renderChart(isModalOpen ? 400 : 320)
          ) : (
            <div className="trends-loading">Loading chart data...</div>
          )}
        </div>
      </div>

      {/* Stats Summary */}
      <div className="trends-stats">
        <div className="trends-stat-item">
          <span className="trends-stat-label">Current</span>
          <span className="trends-stat-value">{stats.current}</span>
          <span className={`trends-stat-change ${stats.change > 0 ? 'positive' : stats.change < 0 ? 'negative' : 'neutral'}`}>
            <TrendingUp size={14} style={{ transform: stats.change < 0 ? 'rotate(180deg)' : 'none' }} />
            {Math.abs(stats.change)}%
          </span>
        </div>

        <div className="trends-stat-item">
          <span className="trends-stat-label">Average</span>
          <span className="trends-stat-value">{stats.avg}</span>
        </div>

        <div className="trends-stat-item">
          <span className="trends-stat-label">Minimum</span>
          <span className="trends-stat-value">{stats.min}</span>
        </div>

        <div className="trends-stat-item">
          <span className="trends-stat-label">Maximum</span>
          <span className="trends-stat-value">{stats.max}</span>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="trends-disclaimer">
        <AlertCircle size={14} />
        Not medical advice. For emergencies, contact a healthcare professional immediately.
      </div>
    </>
  );

  return (
    <>
      {/* Regular Card */}
      <motion.div
        className="dash-card trends-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <div style={{ position: 'relative' }}>
          <motion.button
            className="dash-btn dash-btn-icon dash-focus-ring"
            onClick={() => setIsModalOpen(true)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            title="Expand chart"
            style={{
              position: 'absolute',
              top: 'var(--dash-spacing-lg)',
              right: 'var(--dash-spacing-lg)',
              zIndex: 10,
            }}
          >
            <Maximize2 size={18} />
          </motion.button>
        </div>
        {renderContent()}
      </motion.div>

      {/* Modal View */}
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
              className="trends-modal-content"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: 'spring', damping: 25 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="trends-modal-header">
                <div className="trends-header-left">
                  <div className="trends-title-group">
                    <h2 className="dash-card-title" style={{ fontSize: '1.5rem' }}>
                      Medical Trends - {metrics.find(m => m.key === selectedMetric)?.label}
                    </h2>
                    <span className="trends-subtitle">Real-time health metrics visualization</span>
                  </div>
                </div>
                
                <motion.button
                  className="dash-btn dash-btn-icon dash-focus-ring"
                  onClick={() => setIsModalOpen(false)}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <X size={24} />
                </motion.button>
              </div>

              <div className="trends-modal-body">
                <div className="dash-card-header trends-card-header" style={{ borderBottom: '1px solid var(--dash-border-light)' }}>
                  <div className="trends-metrics">
                    {metrics.map((metric) => (
                      <motion.button
                        key={metric.key}
                        className={`trends-metric-chip ${selectedMetric === metric.key ? 'active' : ''}`}
                        onClick={() => setSelectedMetric(metric.key)}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        {metric.label}
                      </motion.button>
                    ))}
                  </div>

                  <div className="trends-header-right">
                    <div className="trends-time-range">
                      {(['1D', '1W', '1M'] as const).map((range) => (
                        <button
                          key={range}
                          className={`trends-time-btn ${timeRange === range ? 'active' : ''}`}
                          onClick={() => setTimeRange(range)}
                        >
                          {range}
                        </button>
                      ))}
                    </div>

                    {timeRange === '1D' && (
                      <button
                        className={`trends-live-indicator ${!isLive ? 'paused' : ''}`}
                        onClick={toggleLive}
                      >
                        <div className="trends-live-dot" />
                        {isLive ? 'LIVE' : 'PAUSED'}
                      </button>
                    )}
                  </div>
                </div>

                <div className="trends-modal-chart-section">
                  <div className="trends-chart-wrapper" style={{ minHeight: '450px' }}>
                    {chartData.length > 0 ? renderChart(450) : <div className="trends-loading">Loading...</div>}
                  </div>
                </div>

                <div className="trends-stats">
                  <div className="trends-stat-item">
                    <span className="trends-stat-label">Current</span>
                    <span className="trends-stat-value">{stats.current}</span>
                    <span className={`trends-stat-change ${stats.change > 0 ? 'positive' : stats.change < 0 ? 'negative' : 'neutral'}`}>
                      <TrendingUp size={14} style={{ transform: stats.change < 0 ? 'rotate(180deg)' : 'none' }} />
                      {Math.abs(stats.change)}%
                    </span>
                  </div>
                  <div className="trends-stat-item">
                    <span className="trends-stat-label">Average</span>
                    <span className="trends-stat-value">{stats.avg}</span>
                  </div>
                  <div className="trends-stat-item">
                    <span className="trends-stat-label">Minimum</span>
                    <span className="trends-stat-value">{stats.min}</span>
                  </div>
                  <div className="trends-stat-item">
                    <span className="trends-stat-label">Maximum</span>
                    <span className="trends-stat-value">{stats.max}</span>
                  </div>
                </div>

                <div className="trends-disclaimer">
                  <AlertCircle size={14} />
                  Not medical advice. For emergencies, contact a healthcare professional immediately.
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default TrendsCard;
