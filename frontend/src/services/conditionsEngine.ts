/**
 * conditionsEngine – client-side conditions detection.
 *
 * Mirrors backend/app/services/conditions.py logic so we can detect
 * conditions in real-time from SSE telemetry without a server round-trip.
 */

import type { Severity, DetectedConditionFE } from '../components/physics/BodyImpactOverlay';

// ---------- Rule definition ----------

interface ThresholdSet {
  mild: number;
  moderate: number;
  severe: number;
}

interface ConditionRule {
  id: string;
  name: string;
  description: string;
  thresholds: Record<string, ThresholdSet>;
  affected_organs: string[];
  recommendations: string[];
  youtube_queries: string[];
}

// ---------- Rules ----------

const RULES: ConditionRule[] = [
  {
    id: 'hypertension',
    name: 'Hypertension',
    description: 'Elevated blood pressure detected. Sustained high BP increases risk of heart disease and stroke.',
    thresholds: {
      systolic_bp:  { mild: 130, moderate: 140, severe: 160 },
      diastolic_bp: { mild: 85,  moderate: 90,  severe: 100 },
    },
    affected_organs: ['heart', 'kidney', 'brain'],
    recommendations: [
      'Reduce sodium intake to under 2,300 mg/day',
      'Engage in 30 minutes of moderate exercise daily',
      'Practice stress management (meditation, deep breathing)',
      'Monitor blood pressure at home twice daily',
      'Consult your physician about antihypertensive medication',
    ],
    youtube_queries: [
      'how to lower blood pressure naturally',
      'DASH diet for hypertension explained',
      'blood pressure monitoring at home tips',
    ],
  },
  {
    id: 'tachycardia',
    name: 'Tachycardia',
    description: 'Elevated resting heart rate. May indicate stress, dehydration, or cardiac irregularity.',
    thresholds: {
      heart_rate: { mild: 100, moderate: 120, severe: 150 },
    },
    affected_organs: ['heart'],
    recommendations: [
      'Stay hydrated – aim for 8 glasses of water daily',
      'Reduce caffeine and stimulant intake',
      'Practice vagal maneuvers (cold water on face, bearing down)',
      'Get adequate sleep (7-9 hours)',
      'Seek medical evaluation if episodes are frequent',
    ],
    youtube_queries: [
      'what causes tachycardia explained',
      'vagal maneuver techniques for fast heart rate',
    ],
  },
  {
    id: 'bradycardia',
    name: 'Bradycardia',
    description: 'Low resting heart rate. Normal in athletes, but may indicate conduction issues.',
    thresholds: {
      heart_rate: { mild: -55, moderate: -50, severe: -40 },
    },
    affected_organs: ['heart', 'brain'],
    recommendations: [
      'Monitor for dizziness, fatigue, or fainting',
      'Maintain regular physical activity',
      'Review current medications with physician',
      'Consider ECG monitoring if symptomatic',
    ],
    youtube_queries: [
      'bradycardia explained simply',
      'low heart rate causes and treatment',
    ],
  },
  {
    id: 'hypoxemia',
    name: 'Hypoxemia',
    description: 'Blood oxygen saturation below normal. May indicate respiratory compromise.',
    thresholds: {
      spo2: { mild: -94, moderate: -90, severe: -85 },
    },
    affected_organs: ['lungs', 'heart', 'brain'],
    recommendations: [
      'Practice deep breathing exercises (pursed lip breathing)',
      'Ensure adequate ventilation in living spaces',
      'Avoid high-altitude activities until resolved',
      'Seek immediate medical attention if SpO2 drops below 90%',
    ],
    youtube_queries: [
      'how to improve blood oxygen levels naturally',
      'breathing exercises for better oxygen saturation',
    ],
  },
  {
    id: 'kidney_stress',
    name: 'Kidney Stress',
    description: 'Elevated creatinine or BUN suggests reduced kidney filtration capacity.',
    thresholds: {
      creatinine: { mild: 1.3, moderate: 1.8, severe: 3.0 },
      urea:       { mild: 22,  moderate: 30,  severe: 50 },
    },
    affected_organs: ['kidney'],
    recommendations: [
      'Increase water intake to 2-3 liters per day',
      'Reduce dietary protein to ease kidney workload',
      'Avoid NSAIDs (ibuprofen, naproxen)',
      'Schedule kidney function panel with your doctor',
    ],
    youtube_queries: [
      'how to improve kidney function naturally',
      'foods to avoid for kidney health',
    ],
  },
  {
    id: 'liver_stress',
    name: 'Liver Stress',
    description: 'Elevated liver enzymes indicate hepatocellular injury or inflammation.',
    thresholds: {
      alt:             { mild: 60,  moderate: 100, severe: 200 },
      ast:             { mild: 45,  moderate: 80,  severe: 160 },
      bilirubin_total: { mild: 1.5, moderate: 2.5, severe: 5.0 },
    },
    affected_organs: ['liver'],
    recommendations: [
      'Eliminate alcohol consumption completely',
      'Adopt a Mediterranean diet rich in antioxidants',
      'Maintain healthy weight (BMI 18.5-24.9)',
      'Get hepatitis screening if not previously done',
    ],
    youtube_queries: [
      'how to lower liver enzymes naturally',
      'signs your liver needs help',
    ],
  },
  {
    id: 'hyperglycemia',
    name: 'Hyperglycemia',
    description: 'Elevated blood glucose. Persistent elevation may indicate prediabetes or diabetes.',
    thresholds: {
      glucose: { mild: 110, moderate: 140, severe: 200 },
    },
    affected_organs: ['kidney', 'heart', 'brain'],
    recommendations: [
      'Reduce refined carbohydrate and sugar intake',
      'Walk for 15 minutes after each meal',
      'Monitor fasting blood glucose regularly',
      'Consult endocrinologist if fasting glucose exceeds 126 mg/dL',
    ],
    youtube_queries: [
      'how to lower blood sugar quickly',
      'prediabetes reversal diet plan',
    ],
  },
  {
    id: 'high_stress',
    name: 'High Stress',
    description: 'Elevated stress levels impact cardiovascular, immune, and neurological health.',
    thresholds: {
      stress_level: { mild: 4.0, moderate: 6.0, severe: 8.0 },
    },
    affected_organs: ['brain', 'heart'],
    recommendations: [
      'Practice 10-minute daily meditation or mindfulness',
      'Establish consistent sleep schedule',
      'Engage in regular aerobic exercise (150 min/week)',
      'Consider cognitive behavioral therapy (CBT) techniques',
    ],
    youtube_queries: [
      'stress management techniques that work',
      'guided meditation for stress relief 10 minutes',
    ],
  },
  {
    id: 'sleep_deprivation',
    name: 'Sleep Deprivation',
    description: 'Insufficient sleep impairs cognitive function, immune response, and recovery.',
    thresholds: {
      sleep_hours: { mild: -6.5, moderate: -5.0, severe: -4.0 },
    },
    affected_organs: ['brain', 'heart'],
    recommendations: [
      'Aim for 7-9 hours of sleep per night',
      'Create a dark, cool, quiet sleep environment',
      'Avoid caffeine after 2 PM',
      'Limit blue light exposure 2 hours before bed',
    ],
    youtube_queries: [
      'science of sleep hygiene tips',
      'how to fall asleep faster',
    ],
  },
  {
    id: 'tachypnea',
    name: 'Tachypnea',
    description: 'Elevated respiratory rate may indicate respiratory distress or anxiety.',
    thresholds: {
      respiratory_rate: { mild: 22, moderate: 26, severe: 30 },
    },
    affected_organs: ['lungs'],
    recommendations: [
      'Practice diaphragmatic breathing exercises',
      'Sit upright to improve lung expansion',
      'Monitor for fever or signs of infection',
      'Seek medical evaluation if persistent',
    ],
    youtube_queries: [
      'diaphragmatic breathing technique tutorial',
      'what causes rapid breathing in adults',
    ],
  },
];

// ---------- Detection logic ----------

function checkThreshold(value: number, thresholds: ThresholdSet): Severity | null {
  const isBelow = thresholds.mild < 0;

  if (isBelow) {
    if (value <= Math.abs(thresholds.severe)) return 'severe';
    if (value <= Math.abs(thresholds.moderate)) return 'moderate';
    if (value <= Math.abs(thresholds.mild)) return 'mild';
  } else {
    if (value >= thresholds.severe) return 'severe';
    if (value >= thresholds.moderate) return 'moderate';
    if (value >= thresholds.mild) return 'mild';
  }
  return null;
}

const SEVERITY_RANK: Record<Severity, number> = { mild: 1, moderate: 2, severe: 3 };

export function detectConditions(metrics: Record<string, number>): DetectedConditionFE[] {
  const detected: DetectedConditionFE[] = [];

  for (const rule of RULES) {
    let worstSeverity: Severity | null = null;
    const triggerMetrics: Record<string, number> = {};

    for (const [metricName, thresholds] of Object.entries(rule.thresholds)) {
      const value = metrics[metricName];
      if (value === undefined) continue;

      const sev = checkThreshold(value, thresholds);
      if (sev !== null) {
        triggerMetrics[metricName] = value;
        if (worstSeverity === null || SEVERITY_RANK[sev] > SEVERITY_RANK[worstSeverity]) {
          worstSeverity = sev;
        }
      }
    }

    if (worstSeverity && Object.keys(triggerMetrics).length > 0) {
      detected.push({
        id: rule.id,
        name: rule.name,
        description: rule.description,
        severity: worstSeverity,
        affected_organs: rule.affected_organs,
        trigger_metrics: triggerMetrics,
        recommendations: rule.recommendations,
        youtube_queries: rule.youtube_queries,
      });
    }
  }

  // Sort by severity (severe first)
  detected.sort((a, b) => SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity]);
  return detected;
}

export function getOrganSeverities(conditions: DetectedConditionFE[]): Record<string, Severity> {
  const result: Record<string, Severity> = {};
  for (const cond of conditions) {
    for (const organ of cond.affected_organs) {
      const current = result[organ];
      if (!current || SEVERITY_RANK[cond.severity] > SEVERITY_RANK[current]) {
        result[organ] = cond.severity;
      }
    }
  }
  return result;
}

// ---------- Trend detection ----------

export type TrendDirection = 'up' | 'down' | 'stable';

export function computeTrend(
  history: { metrics: Record<string, number> }[],
  metricName: string,
  windowSize = 10,
): TrendDirection {
  if (history.length < 3) return 'stable';

  const recent = history.slice(-windowSize);
  const values = recent.map((r) => r.metrics[metricName]).filter((v) => v !== undefined);
  if (values.length < 3) return 'stable';

  // Simple linear regression slope
  const n = values.length;
  const xMean = (n - 1) / 2;
  const yMean = values.reduce((a, b) => a + b, 0) / n;

  let num = 0;
  let den = 0;
  for (let i = 0; i < n; i++) {
    num += (i - xMean) * (values[i] - yMean);
    den += (i - xMean) ** 2;
  }
  const slope = den !== 0 ? num / den : 0;

  // Threshold relative to mean
  const threshold = Math.abs(yMean) * 0.01; // 1% of mean
  if (slope > threshold) return 'up';
  if (slope < -threshold) return 'down';
  return 'stable';
}
