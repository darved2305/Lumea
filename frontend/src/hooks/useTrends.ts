/**
 * API-Based Trends Hook
 * 
 * Fetches trend data from backend ONLY when:
 * 1. Metric selection changes
 * 2. Time range changes
 * 3. WebSocket notifies of data update
 * 
 * NO fake data, NO random generation, NO setInterval updates.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../config/api';

export interface TrendDataPoint {
  timestamp: number;  // Unix timestamp (ms)
  value: number;
  flag?: 'Low' | 'Normal' | 'High' | 'Critical';
}

export interface TrendStats {
  current: number;
  avg: number;
  min: number;
  max: number;
  change: number;  // Percentage change from previous
}

export interface TrendData {
  metric: string;
  unit: string;
  refRange: { low: number; high: number } | null;
  points: TrendDataPoint[];
  stats: TrendStats;
}

interface UseTrendsOptions {
  authToken: string | null;
  apiBaseUrl?: string;
  onError?: (error: string) => void;
}

interface UseTrendsResult {
  data: TrendDataPoint[];
  stats: TrendStats;
  loading: boolean;
  error: string | null;
  refetch: () => void;
  lastFetchedAt: Date | null;
}

const emptyStats: TrendStats = {
  current: 0,
  avg: 0,
  min: 0,
  max: 0,
  change: 0,
};

/**
 * Hook for fetching trend data from the backend API.
 * 
 * Data is fetched ONLY on:
 * - Initial mount
 * - metric or range change
 * - Manual refetch() call (triggered by WebSocket events)
 */
export function useTrends(
  metric: string,
  range: '1D' | '1W' | '1M',
  options: UseTrendsOptions
): UseTrendsResult {
  const { authToken, apiBaseUrl = API_BASE_URL, onError } = options;
  
  const [data, setData] = useState<TrendDataPoint[]>([]);
  const [stats, setStats] = useState<TrendStats>(emptyStats);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(null);
  
  // Track last fetch params to avoid duplicate requests
  const lastFetchRef = useRef<string>('');

  const fetchTrends = useCallback(async () => {
    if (!authToken) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    // Map frontend metric keys to backend metric enum values
    const metricMapping: Record<string, string> = {
      'index': 'health_index',
      'sleep': 'sleep',
      'bloodPressure': 'blood_pressure',
      'glucose': 'glucose',
      'activity': 'activity',
    };

    const backendMetric = metricMapping[metric] || metric;
    const backendRange = range.toLowerCase(); // 1D -> 1d

    const fetchKey = `${backendMetric}-${backendRange}-${Date.now()}`;
    lastFetchRef.current = fetchKey;

    setLoading(true);
    setError(null);

    try {
      const url = new URL(`${apiBaseUrl}/api/dashboard/trends`);
      url.searchParams.set('metric', backendMetric);
      url.searchParams.set('range', backendRange);

      const response = await fetch(url.toString(), {
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          // No data available - show empty state
          setData([]);
          setStats(emptyStats);
          setLastFetchedAt(new Date());
          return;
        }
        throw new Error(`Failed to fetch trends: ${response.status}`);
      }

      const result = await response.json();
      
      // Convert backend format to frontend format
      const points: TrendDataPoint[] = (result.data || []).map((point: any) => ({
        timestamp: new Date(point.timestamp || point.t).getTime(),
        value: point.value ?? point.v ?? 0,
        flag: point.flag,
      }));

      // Calculate stats from points
      const calculatedStats = calculateStats(points);
      
      setData(points);
      setStats(result.stats || calculatedStats);
      setLastFetchedAt(new Date());
      
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load trends';
      setError(errorMsg);
      onError?.(errorMsg);
      // Keep existing data on error
    } finally {
      setLoading(false);
    }
  }, [authToken, apiBaseUrl, metric, range, onError]);

  // Fetch on mount and when metric/range changes
  useEffect(() => {
    fetchTrends();
  }, [metric, range, authToken]); // Note: fetchTrends is intentionally not in deps to prevent loops

  return {
    data,
    stats,
    loading,
    error,
    refetch: fetchTrends,
    lastFetchedAt,
  };
}

/**
 * Calculate stats from data points
 */
function calculateStats(points: TrendDataPoint[]): TrendStats {
  if (points.length === 0) {
    return emptyStats;
  }

  const values = points.map(p => p.value);
  const current = values[values.length - 1];
  const previous = values.length > 1 ? values[values.length - 2] : current;
  const avg = values.reduce((sum, v) => sum + v, 0) / values.length;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const change = previous !== 0 ? ((current - previous) / previous) * 100 : 0;

  return {
    current: Math.round(current * 10) / 10,
    avg: Math.round(avg * 10) / 10,
    min: Math.round(min * 10) / 10,
    max: Math.round(max * 10) / 10,
    change: Math.round(change * 10) / 10,
  };
}

export default useTrends;
