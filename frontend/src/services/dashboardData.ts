// Mock Data Layer for Dashboard
// TODO: Replace with real API calls and WebSocket connections

export interface HealthFactor {
  key: string;
  label: string;
  value: number; // 0-100
  contribution: number; // percentage impact on overall score
  unit?: string;
  status: 'good' | 'warning' | 'critical';
}

export interface HealthSummary {
  healthIndexScore: number; // 0-100
  factors: HealthFactor[];
  lastUpdated: Date;
  trend: 'up' | 'down' | 'stable';
}

export interface TimeSeriesPoint {
  timestamp: number;
  value: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

// Mock data generator
export function getHealthSummary(): HealthSummary {
  return {
    healthIndexScore: 71,
    lastUpdated: new Date(),
    trend: 'stable',
    factors: [
      {
        key: 'sleep',
        label: 'Sleep Quality',
        value: 65,
        contribution: 25,
        unit: 'hours',
        status: 'warning',
      },
      {
        key: 'activity',
        label: 'Physical Activity',
        value: 78,
        contribution: 20,
        unit: 'steps',
        status: 'good',
      },
      {
        key: 'bloodPressure',
        label: 'Blood Pressure',
        value: 82,
        contribution: 18,
        unit: 'mmHg',
        status: 'good',
      },
      {
        key: 'glucose',
        label: 'Glucose Level',
        value: 88,
        contribution: 15,
        unit: 'mg/dL',
        status: 'good',
      },
      {
        key: 'stress',
        label: 'Stress Level',
        value: 45,
        contribution: 12,
        unit: 'level',
        status: 'critical',
      },
      {
        key: 'hydration',
        label: 'Hydration',
        value: 70,
        contribution: 10,
        unit: 'liters',
        status: 'good',
      },
    ],
  };
}

export function getTimeSeries(
  _metric: string,
  range: '1D' | '1W' | '1M'
): TimeSeriesPoint[] {
  const now = Date.now();
  const points: TimeSeriesPoint[] = [];
  
  let intervals: number;
  let timeStep: number;
  
  switch (range) {
    case '1D':
      intervals = 60; // 60 points
      timeStep = 24 * 60 * 60 * 1000 / intervals; // Every ~24 minutes
      break;
    case '1W':
      intervals = 84; // 12 per day * 7 days
      timeStep = 7 * 24 * 60 * 60 * 1000 / intervals;
      break;
    case '1M':
      intervals = 90; // 3 per day * 30 days
      timeStep = 30 * 24 * 60 * 60 * 1000 / intervals;
      break;
  }
  
  // Generate semi-realistic data with trends and noise
  const baseValue = 70;
  const amplitude = 15;
  
  for (let i = 0; i < intervals; i++) {
    const timestamp = now - (intervals - i) * timeStep;
    const trend = Math.sin((i / intervals) * Math.PI * 2) * amplitude;
    const noise = (Math.random() - 0.5) * 10;
    const value = Math.max(40, Math.min(100, baseValue + trend + noise));
    
    points.push({ timestamp, value });
  }
  
  return points;
}

// Simulate streaming data update
export function generateNextPoint(
  lastPoint: TimeSeriesPoint,
  _metric: string
): TimeSeriesPoint {
  const now = Date.now();
  
  // Small random walk
  const change = (Math.random() - 0.5) * 3;
  const newValue = Math.max(40, Math.min(100, lastPoint.value + change));
  
  return {
    timestamp: now,
    value: newValue,
  };
}

// Pre-generated question suggestions
export function getQuestionSuggestions(score: number): string[] {
  if (score >= 80) {
    return [
      "How can I maintain this excellent health index?",
      "What's contributing most to my score?",
      "Any preventive tips for staying healthy?",
      "Show me my best performing metrics"
    ];
  } else if (score >= 60) {
    return [
      "Why is my health index " + score + "%?",
      "What should I improve this week?",
      "Explain my sleep impact on health",
      "Is anything concerning right now?"
    ];
  } else {
    return [
      "What's most urgent to address?",
      "Create an action plan for improvement",
      "Why is my score low?",
      "Should I consult a doctor?"
    ];
  }
}

// Mock AI assistant responses
export async function mockAssistantResponse(question: string): Promise<string> {
  // Simulate thinking delay
  await new Promise(resolve => setTimeout(resolve, 1200));
  
  const lowerQ = question.toLowerCase();
  
  if (lowerQ.includes('71') || lowerQ.includes('why') || lowerQ.includes('index')) {
    return `Your health index of 71% indicates **good overall health** with room for improvement. Here's the breakdown:

**Top Contributors:**
• Blood Pressure (82%) - Excellent control
• Physical Activity (78%) - Good movement
• Sleep Quality (65%) - **Needs attention**

**Key Recommendations:**
1. Focus on improving sleep duration and quality
2. Continue your physical activity routine
3. Monitor stress levels more closely

Your trend is stable, which is positive. Small improvements in sleep could push you to 75-80%.`;
  }
  
  if (lowerQ.includes('improve') || lowerQ.includes('week')) {
    return `**This Week's Focus Areas:**

1. **Sleep Optimization** (Priority #1)
   - Target 7-8 hours nightly
   - Maintain consistent sleep schedule
   - Reduce screen time 1hr before bed

2. **Stress Management**
   - Try 10 min daily meditation
   - Deep breathing exercises
   - Regular breaks during work

3. **Maintain Current Strengths**
   - Keep up exercise routine
   - Continue hydration habits

*Small changes = Big impact on your score.*`;
  }
  
  if (lowerQ.includes('sleep')) {
    return `**Sleep Impact Analysis:**

Your sleep quality (65%) is affecting your overall score by **-5 points**. 

**Current Pattern:**
• Average: 6.2 hrs/night
• Quality: Moderate
• Consistency: Variable

**To Improve:**
✓ Add 45-60 min to sleep duration
✓ Set a bedtime routine
✓ Optimize bedroom environment (cool, dark, quiet)

Better sleep = Better recovery = Higher energy = Improved overall health index.`;
  }
  
  if (lowerQ.includes('alarming') || lowerQ.includes('concerning')) {
    return `**Health Status Check:**

✅ **No Critical Alerts**

**Areas to Monitor:**
• Stress levels (45%) - Below optimal
• Sleep quality (65%) - Could be better

**All Vital Signs Normal:**
✓ Blood pressure: Healthy range
✓ Glucose: Well controlled
✓ Activity: Good levels

*No immediate medical concerns. Continue monitoring and focus on stress reduction techniques.*`;
  }
  
  // Default response
  return `I'm analyzing your health data. Your current index of 71% shows you're maintaining good overall health. 

**Quick Insights:**
• Most metrics are in healthy ranges
• Sleep and stress need attention
• Your trend is stable

Feel free to ask specific questions about any health metric, and I can provide detailed analysis and personalized recommendations.`;
}
