// Custom Hooks for Dashboard Features
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getTimeSeries,
  generateNextPoint,
  getQuestionSuggestions,
  mockAssistantResponse,
  type HealthSummary,
  type TimeSeriesPoint,
  type ChatMessage,
} from '../services/dashboardData';

const API_BASE = 'http://localhost:8000';

// Hook for health summary data - fetches from REAL API
export function useHealthSummary() {
  const [data, setData] = useState<HealthSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        // Fetch from real health-index endpoint
        const response = await fetch(`${API_BASE}/api/health-index`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const result = await response.json();
          
          // Transform to HealthSummary format
          if (result.score !== null && result.score !== undefined) {
            const factors = [];
            if (result.contributions) {
              for (const [key, value] of Object.entries(result.contributions as Record<string, any>)) {
                factors.push({
                  key,
                  label: value.detail?.label || key,
                  value: value.score || 0,
                  contribution: value.contribution || 0,
                  unit: value.detail?.unit,
                  status: value.detail?.status || 'good',
                });
              }
            }

            setData({
              healthIndexScore: result.score,
              lastUpdated: result.computed_at ? new Date(result.computed_at) : new Date(),
              trend: 'stable',
              factors,
            });
          } else {
            // No data yet
            setData(null);
          }
        }
      } catch (err) {
        console.error('Error fetching health summary:', err);
        setError('Failed to load health data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return { data, loading, error };
}

// Hook for live time series data with simulated streaming
export function useLiveSeries(metric: string, range: '1D' | '1W' | '1M') {
  const [data, setData] = useState<TimeSeriesPoint[]>([]);
  const [isLive, setIsLive] = useState(true);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    // Initial data load
    const initialData = getTimeSeries(metric, range);
    setData(initialData);

    // Set up live updates only for 1D range
    if (range === '1D' && isLive) {
      intervalRef.current = window.setInterval(() => {
        setData(prevData => {
          if (prevData.length === 0) return prevData;
          
          const lastPoint = prevData[prevData.length - 1];
          const nextPoint = generateNextPoint(lastPoint, metric);
          
          // Keep only last 60 points for 1D view
          const newData = [...prevData.slice(-59), nextPoint];
          return newData;
        });
      }, 2000); // Update every 2 seconds

      // TODO: Replace with WebSocket connection
      // Example:
      // const ws = new WebSocket('ws://localhost:8000/live-metrics');
      // ws.onmessage = (event) => {
      //   const point = JSON.parse(event.data);
      //   setData(prev => [...prev.slice(-59), point]);
      // };
      // return () => ws.close();
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [metric, range, isLive]);

  const toggleLive = useCallback(() => {
    setIsLive(prev => !prev);
  }, []);

  return { data, isLive, toggleLive };
}

// Hook for AI assistant chat functionality in dashboard
export function useAIAssistant() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Hello! I'm your AI Health Assistant. I'm here to help you understand your health data and provide personalized recommendations. 

Feel free to ask me anything about your health index, metrics, or what you can do to improve your wellness.`,
      timestamp: new Date(),
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // Update suggestions - use default score of 70 (middle suggestions)
  // Real score-based suggestions would need integration with health summary API
  useEffect(() => {
    setSuggestions(getQuestionSuggestions(70));
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    try {
      // Get AI response
      const responseContent = await mockAssistantResponse(content);
      
      // Simulate typing delay for more natural feel
      await new Promise(resolve => setTimeout(resolve, 300));
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: responseContent,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error getting response:', error);
      
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  }, []);

  return {
    messages,
    isTyping,
    suggestions,
    sendMessage,
  };
}

// Hook for selected metric tracking
export function useSelectedMetric(defaultMetric: string = 'index') {
  const [selectedMetric, setSelectedMetric] = useState(defaultMetric);
  
  return { selectedMetric, setSelectedMetric };
}
