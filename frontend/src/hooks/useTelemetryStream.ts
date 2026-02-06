/**
 * useTelemetryStream – React hook for SSE real-time telemetry.
 *
 * Connects to /api/telemetry/stream via EventSource.
 * Falls back to simulated mode if SSE fails or backend is unavailable.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

// ---------- Types ----------

export interface TelemetryReading {
  timestamp: string;
  metrics: Record<string, number>;
  units: Record<string, string>;
}

export interface TelemetryState {
  /** Latest reading */
  current: TelemetryReading | null;
  /** Rolling buffer of recent readings (for sparklines / history) */
  history: TelemetryReading[];
  /** Whether SSE is connected */
  connected: boolean;
  /** Whether using simulated fallback */
  simulated: boolean;
  /** Seconds since last reading */
  staleness: number;
}

// ---------- Simulated fallback generator ----------

const BASELINES: Record<string, { base: number; jitter: number; unit: string }> = {
  heart_rate:       { base: 72, jitter: 5, unit: 'bpm' },
  systolic_bp:      { base: 118, jitter: 6, unit: 'mmHg' },
  diastolic_bp:     { base: 76, jitter: 4, unit: 'mmHg' },
  spo2:             { base: 97.5, jitter: 0.8, unit: '%' },
  respiratory_rate: { base: 16, jitter: 2, unit: 'bpm' },
  temperature:      { base: 98.4, jitter: 0.3, unit: '°F' },
  stress_level:     { base: 2.5, jitter: 0.8, unit: 'score' },
  sleep_hours:      { base: 7.2, jitter: 0.5, unit: 'hrs' },
  creatinine:       { base: 1.0, jitter: 0.15, unit: 'mg/dL' },
  urea:             { base: 14, jitter: 2.5, unit: 'mg/dL' },
  egfr:             { base: 95, jitter: 5, unit: 'mL/min' },
  sodium:           { base: 140, jitter: 2, unit: 'mEq/L' },
  alt:              { base: 25, jitter: 5, unit: 'U/L' },
  ast:              { base: 22, jitter: 4, unit: 'U/L' },
  bilirubin_total:  { base: 0.8, jitter: 0.15, unit: 'mg/dL' },
  glucose:          { base: 95, jitter: 8, unit: 'mg/dL' },
};

let _simTick = 0;
const _phaseOffset = Math.random() * Math.PI * 2;

function generateSimReading(): TelemetryReading {
  _simTick++;
  const metrics: Record<string, number> = {};
  const units: Record<string, string> = {};

  for (const [name, cfg] of Object.entries(BASELINES)) {
    const wave = Math.sin(_simTick * 0.05 + _phaseOffset) * cfg.jitter * 0.4;
    const noise = (Math.random() - 0.5) * cfg.jitter * 1.2;
    let val = cfg.base + wave + noise;
    if (name === 'spo2') val = Math.min(100, Math.max(70, val));
    metrics[name] = Math.round(val * 100) / 100;
    units[name] = cfg.unit;
  }

  return {
    timestamp: new Date().toISOString(),
    metrics,
    units,
  };
}

// ---------- Hook ----------

const MAX_HISTORY = 120; // ~4 min at 2s interval

export function useTelemetryStream(interval = 2000): TelemetryState {
  const [state, setState] = useState<TelemetryState>({
    current: null,
    history: [],
    connected: false,
    simulated: false,
    staleness: 0,
  });

  const historyRef = useRef<TelemetryReading[]>([]);
  const lastTimestampRef = useRef<number>(Date.now());
  const eventSourceRef = useRef<EventSource | null>(null);
  const simIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stalenessIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pushReading = useCallback((reading: TelemetryReading) => {
    historyRef.current = [...historyRef.current.slice(-(MAX_HISTORY - 1)), reading];
    lastTimestampRef.current = Date.now();
    setState({
      current: reading,
      history: historyRef.current,
      connected: true,
      simulated: false,
      staleness: 0,
    });
  }, []);

  const pushSimReading = useCallback(() => {
    const reading = generateSimReading();
    historyRef.current = [...historyRef.current.slice(-(MAX_HISTORY - 1)), reading];
    lastTimestampRef.current = Date.now();
    setState({
      current: reading,
      history: historyRef.current,
      connected: false,
      simulated: true,
      staleness: 0,
    });
  }, []);

  // Start SSE or fallback
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      // No auth – use simulation
      simIntervalRef.current = setInterval(pushSimReading, interval);
      pushSimReading(); // immediate first
      return () => {
        if (simIntervalRef.current) clearInterval(simIntervalRef.current);
      };
    }

    // Try SSE connection
    // Note: EventSource doesn't support custom headers natively,
    // so we pass token as query param
    const url = `${API_BASE_URL}/api/telemetry/stream?interval=${interval / 1000}&token=${encodeURIComponent(token)}`;

    let retryCount = 0;
    const maxRetries = 3;

    function connectSSE() {
      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const reading: TelemetryReading = JSON.parse(event.data);
          pushReading(reading);
          retryCount = 0;
        } catch (e) {
          console.error('Telemetry parse error:', e);
        }
      };

      es.onerror = () => {
        es.close();
        eventSourceRef.current = null;
        retryCount++;

        if (retryCount <= maxRetries) {
          // Retry after delay
          setTimeout(connectSSE, 2000 * retryCount);
        } else {
          // Fall back to simulation
          console.warn('SSE failed, falling back to simulation');
          simIntervalRef.current = setInterval(pushSimReading, interval);
          pushSimReading();
        }
      };
    }

    // Initial: try fetching latest first, then start SSE
    fetch(`${API_BASE_URL}/api/telemetry/latest`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data) pushReading(data);
        connectSSE();
      })
      .catch(() => {
        // Backend unavailable – use simulation
        simIntervalRef.current = setInterval(pushSimReading, interval);
        pushSimReading();
      });

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (simIntervalRef.current) {
        clearInterval(simIntervalRef.current);
        simIntervalRef.current = null;
      }
    };
  }, [interval, pushReading, pushSimReading]);

  // Staleness counter
  useEffect(() => {
    stalenessIntervalRef.current = setInterval(() => {
      setState((prev) => ({
        ...prev,
        staleness: Math.round((Date.now() - lastTimestampRef.current) / 1000),
      }));
    }, 1000);

    return () => {
      if (stalenessIntervalRef.current) clearInterval(stalenessIntervalRef.current);
    };
  }, []);

  return state;
}
