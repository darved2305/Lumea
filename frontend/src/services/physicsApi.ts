/**
 * Physics Twin – TypeScript types + API client.
 * Uses native fetch consistent with profileApi.ts pattern.
 */

import { API_BASE_URL } from '../config/api';

// ---------- Types ----------

export interface MetricContribution {
  name: string;
  unit: string;
  value: number | null;
  normalised: number | null;
  weight: number;
  weighted: number | null;
}

export interface OrganResult {
  score: number;
  status: 'Healthy' | 'Watch' | 'Risk';
  coverage: number;
  contributions: MetricContribution[];
}

export interface PhysicsSnapshot {
  id: string;
  user_id: string;
  timestamp: string;
  overall_score: number;
  overall_status: 'Healthy' | 'Watch' | 'Risk';
  organs: Record<string, OrganResult>;
  raw_metrics: Record<string, number>;
  conditions?: PhysicsCondition[];
  organ_conditions?: Record<string, string[]>;
  organ_severities?: Record<string, string>;
  data_source?: string;  // "reports", "manual", "profile"
}

export interface PhysicsCondition {
  id: string;
  name: string;
  description: string;
  severity: 'mild' | 'moderate' | 'severe';
  affected_organs: string[];
  trigger_metrics: Record<string, number>;
  recommendations: string[];
  youtube_queries: string[];
}

export interface MetricConfigItem {
  name: string;
  unit: string;
  ref_min: number;
  ref_max: number;
  weight: number;
  direction: 'lower_better' | 'higher_better';
}

export interface OrganConfig {
  label: string;
  metrics: MetricConfigItem[];
}

export interface PhysicsConfig {
  organs: Record<string, OrganConfig>;
}

// ---------- Helpers ----------

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ---------- API calls ----------

export async function submitMetrics(
  metrics: Record<string, number>,
  timestamp?: string,
): Promise<PhysicsSnapshot> {
  const res = await fetch(`${API_BASE_URL}/api/physics/metrics`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ metrics, timestamp }),
  });
  if (!res.ok) throw new Error(`Submit failed (${res.status})`);
  return res.json();
}

export async function getLatestSnapshot(): Promise<PhysicsSnapshot | null> {
  const res = await fetch(`${API_BASE_URL}/api/physics/latest`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Fetch latest failed (${res.status})`);
  const data = await res.json();
  return data || null;
}

export async function getHistory(days = 30): Promise<PhysicsSnapshot[]> {
  const res = await fetch(`${API_BASE_URL}/api/physics/history?days=${days}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Fetch history failed (${res.status})`);
  return res.json();
}

export async function getPhysicsConfig(): Promise<PhysicsConfig> {
  const res = await fetch(`${API_BASE_URL}/api/physics/config`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Fetch config failed (${res.status})`);
  return res.json();
}
