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
import { API_BASE_URL, WS_BASE_URL } from '../config/api';

const API_BASE = API_BASE_URL;

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

// Hook for AI assistant chat functionality in dashboard with WebSocket streaming
export function useAIAssistant() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Hello! I'm your AI Health Assistant powered by MedGemma. I'm here to help you understand your health data and provide personalized insights based on your medical reports.

Ask me anything about your health metrics, lab results, or what you can do to improve your wellness.`,
      timestamp: new Date(),
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const currentMessageIdRef = useRef<string | null>(null);
  const tokenBufferRef = useRef('');
  const flushTimerRef = useRef<number | null>(null);

  // Update suggestions
  useEffect(() => {
    setSuggestions(getQuestionSuggestions(70));
  }, []);

  // Setup WebSocket connection for chat
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const ws = new WebSocket(`${WS_BASE_URL}/ws?token=${token}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const upsertAssistantMessage = (id: string, updater: (prev: ChatMessage) => ChatMessage) => {
          setMessages(prev => {
            const idx = prev.findIndex(m => m.id === id);
            if (idx === -1) {
              return [...prev, updater({
                id,
                role: 'assistant',
                content: '',
                timestamp: new Date(),
              })];
            }
            const next = [...prev];
            next[idx] = updater(next[idx]);
            return next;
          });
        };
        const flushBufferedTokens = () => {
          if (!currentMessageIdRef.current || !tokenBufferRef.current) return;
          const chunk = tokenBufferRef.current;
          tokenBufferRef.current = '';
          upsertAssistantMessage(currentMessageIdRef.current, msg => ({
            ...msg,
            content: (msg.content || '') + chunk,
          }));
        };
        const scheduleFlush = () => {
          if (flushTimerRef.current) return;
          flushTimerRef.current = window.setTimeout(() => {
            flushTimerRef.current = null;
            flushBufferedTokens();
          }, 50);
        };
        
        switch (message.type) {
          case 'chat_start':
            // Response generation started
            setIsTyping(true);
            currentMessageIdRef.current = Date.now().toString();
            tokenBufferRef.current = '';
            upsertAssistantMessage(currentMessageIdRef.current, msg => msg);
            break;
            
          case 'chat_token':
            if (currentMessageIdRef.current && message.data?.token != null) {
              tokenBufferRef.current += message.data.token;
              scheduleFlush();
            }
            break;

          case 'chat_complete':
            if (flushTimerRef.current) {
              clearTimeout(flushTimerRef.current);
              flushTimerRef.current = null;
            }
            flushBufferedTokens();
            if (currentMessageIdRef.current) {
              const finalContent = message.data?.full_response;
              if (finalContent) {
                upsertAssistantMessage(currentMessageIdRef.current, msg => ({
                  ...msg,
                  content: finalContent,
                  timestamp: new Date(),
                }));
              }
            }
            setIsTyping(false);
            currentMessageIdRef.current = null;
            break;
            
          case 'chat_error': {
            if (flushTimerRef.current) {
              clearTimeout(flushTimerRef.current);
              flushTimerRef.current = null;
            }
            tokenBufferRef.current = '';
            const errText = message.data?.error != null ? String(message.data.error) : 'Unknown error';
            if (currentMessageIdRef.current) {
              upsertAssistantMessage(currentMessageIdRef.current, msg => ({
                ...msg,
                content: `Sorry, I encountered an error: ${errText}. Please try again.`,
                timestamp: new Date(),
              }));
            } else {
              const errorMessage: ChatMessage = {
                id: Date.now().toString(),
                role: 'assistant',
                content: `Sorry, I encountered an error: ${errText}. Please try again.`,
                timestamp: new Date(),
              };
              setMessages(prev => [...prev, errorMessage]);
            }
            setIsTyping(false);
            currentMessageIdRef.current = null;
            break;
          }
        }
      } catch (e) {
        console.error('Error parsing chat message:', e);
      }
    };

    return () => {
      if (flushTimerRef.current) {
        clearTimeout(flushTimerRef.current);
        flushTimerRef.current = null;
      }
      ws.close();
    };
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

    // Send via WebSocket
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'chat_request',
        message: content,
      }));
    } else {
      // Fallback to mock if WebSocket not connected
      try {
        const responseContent = await mockAssistantResponse(content);
        
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
