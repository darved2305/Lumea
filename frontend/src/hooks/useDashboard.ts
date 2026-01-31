// Custom Hooks for Dashboard Features
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getHealthSummary,
  getTimeSeries,
  generateNextPoint,
  getQuestionSuggestions,
  mockAssistantResponse,
  type HealthSummary,
  type TimeSeriesPoint,
  type ChatMessage,
} from '../services/dashboardData';

// Hook for health summary data
export function useHealthSummary() {
  const [data, setData] = useState<HealthSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate API call
    const fetchData = async () => {
      setLoading(true);
      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 500));
      const summary = getHealthSummary();
      setData(summary);
      setLoading(false);
    };

    fetchData();
  }, []);

  return { data, loading };
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

  // Update suggestions based on latest health score
  useEffect(() => {
    const summary = getHealthSummary();
    setSuggestions(getQuestionSuggestions(summary.healthIndexScore));
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
