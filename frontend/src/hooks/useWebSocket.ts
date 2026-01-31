/**
 * WebSocket hook for real-time updates
 * 
 * Replaces SSE with WebSocket for bidirectional communication
 */
import { useEffect, useRef, useCallback, useState } from 'react';

export type WebSocketEventType = 
  | 'connected'
  | 'ping'
  | 'pong'
  | 'report_processing_started'
  | 'report_parsed'
  | 'health_index_updated'
  | 'trends_updated'
  | 'reports_list_updated'
  | 'recommendations_updated';

export interface WebSocketMessage {
  type: WebSocketEventType;
  data: Record<string, any>;
  timestamp: string;
}

export interface HealthIndexUpdate {
  score: number;
  breakdown: Record<string, number>;
  confidence: number;
  updated_at: string;
}

export interface ReportProcessingUpdate {
  report_id: string;
  progress?: number;
  extracted_metrics_count?: number;
}

export interface RecommendationsUpdate {
  count: number;
  urgent_count: number;
}

interface UseWebSocketOptions {
  onHealthIndexUpdated?: (data: HealthIndexUpdate) => void;
  onReportProcessingStarted?: (data: ReportProcessingUpdate) => void;
  onReportParsed?: (data: ReportProcessingUpdate) => void;
  onReportsListUpdated?: () => void;
  onTrendsUpdated?: (metrics: string[]) => void;
  onRecommendationsUpdated?: (data: RecommendationsUpdate) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (error: Event) => void;
}

const WS_BASE_URL = 'ws://localhost:8000';
const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;
const PING_INTERVAL_MS = 25000; // Ping every 25 seconds
const PONG_TIMEOUT_MS = 60000; // Expect pong within 60 seconds
const CONNECTION_STABILITY_MS = 10000; // Must be connected for 10s to reset backoff

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY_MS);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);
  const pongTimeoutRef = useRef<number | null>(null);
  const connectionTimeRef = useRef<number | null>(null);
  const shouldReconnectRef = useRef(true);
  
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const getToken = useCallback(() => {
    return localStorage.getItem('access_token');
  }, []);

  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (pongTimeoutRef.current) {
      clearTimeout(pongTimeoutRef.current);
      pongTimeoutRef.current = null;
    }
    if (connectionTimeRef.current) {
      clearTimeout(connectionTimeRef.current);
      connectionTimeRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const resetPongTimeout = useCallback(() => {
    if (pongTimeoutRef.current) {
      clearTimeout(pongTimeoutRef.current);
    }
    pongTimeoutRef.current = window.setTimeout(() => {
      console.warn('No pong received within timeout, reconnecting...');
      cleanup();
      if (shouldReconnectRef.current) {
        // Don't use current delay, just reconnect immediately on timeout
        reconnectTimeoutRef.current = window.setTimeout(connect, 1000);
      }
    }, PONG_TIMEOUT_MS);
  }, [cleanup]);

  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
        resetPongTimeout();
      } catch (e) {
        console.error('Failed to send ping:', e);
      }
    }
  }, [resetPongTimeout]);

  const connect = useCallback(() => {
    const token = getToken();
    if (!token) {
      console.log('No auth token, skipping WebSocket connection');
      return;
    }

    // Don't create multiple connections
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log('WebSocket already connecting/connected');
      return;
    }
    // Don't create multiple connections
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log('WebSocket already connecting/connected');
      return;
    }

    cleanup();

    console.log(`Connecting to WebSocket (delay was ${reconnectDelayRef.current}ms)...`);
    const ws = new WebSocket(`${WS_BASE_URL}/ws?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('✅ WebSocket connected');
      setIsConnected(true);
      
      // Reset backoff after stable connection
      connectionTimeRef.current = window.setTimeout(() => {
        reconnectDelayRef.current = INITIAL_RECONNECT_DELAY_MS;
        console.log('Connection stable, backoff reset');
      }, CONNECTION_STABILITY_MS);
      
      // Start ping interval
      pingIntervalRef.current = window.setInterval(sendPing, PING_INTERVAL_MS);
      resetPongTimeout();
      
      options.onConnected?.();
    };

    ws.onclose = (event) => {
      console.log(`WebSocket closed: code=${event.code}, reason="${event.reason}"`);
      setIsConnected(false);
      options.onDisconnected?.();

      // Clear intervals
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
      if (pongTimeoutRef.current) {
        clearTimeout(pongTimeoutRef.current);
        pongTimeoutRef.current = null;
      }
      if (connectionTimeRef.current) {
        clearTimeout(connectionTimeRef.current);
        connectionTimeRef.current = null;
      }

      // Handle reconnection based on close code
      if (!shouldReconnectRef.current) {
        console.log('Reconnect disabled, not reconnecting');
        return;
      }

      if (event.code === 1000) {
        // Normal close, don't reconnect
        console.log('Normal close, not reconnecting');
        return;
      }

      if (event.code === 1008 || event.code === 4001) {
        // Auth/policy violation, don't reconnect
        console.error('❌ Authentication failed, not reconnecting');
        return;
      }

      // Reconnect with exponential backoff
      const delay = Math.min(reconnectDelayRef.current, MAX_RECONNECT_DELAY_MS);
      console.log(`Reconnecting in ${delay}ms...`);
      
      reconnectTimeoutRef.current = window.setTimeout(() => {
        // Increase delay for next time (exponential backoff)
        reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, MAX_RECONNECT_DELAY_MS);
        connect();
      }, delay);
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      options.onError?.(error);
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        setLastUpdated(new Date(message.timestamp));

        switch (message.type) {
          case 'connected':
            console.log('WebSocket handshake complete:', message.data.message);
            break;

          case 'pong':
            // Keepalive response - reset timeout
            resetPongTimeout();
            break;

          case 'ping':
            // Server ping - respond with pong
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ type: 'pong' }));
            }
            break;

          case 'health_index_updated':
            options.onHealthIndexUpdated?.(message.data as HealthIndexUpdate);
            break;

          case 'report_processing_started':
            options.onReportProcessingStarted?.(message.data as ReportProcessingUpdate);
            break;

          case 'report_parsed':
            options.onReportParsed?.(message.data as ReportProcessingUpdate);
            break;

          case 'reports_list_updated':
            options.onReportsListUpdated?.();
            break;

          case 'trends_updated':
            options.onTrendsUpdated?.(message.data.metrics);
            break;

          case 'recommendations_updated':
            options.onRecommendationsUpdated?.(message.data as RecommendationsUpdate);
            break;

          default:
            console.log('Unknown WebSocket event:', message.type);
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };
  }, [getToken, cleanup, sendPing, resetPongTimeout, options]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    cleanup();
    setIsConnected(false);
  }, [cleanup]);

  // Auto-connect on mount, disconnect on unmount
  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();
    
    return () => {
      shouldReconnectRef.current = false;
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  // Reconnect when token changes
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'access_token') {
        if (e.newValue) {
          shouldReconnectRef.current = true;
          connect();
        } else {
          disconnect();
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only setup listener once

  return {
    isConnected,
    lastUpdated,
    connect,
    disconnect,
  };
}

export default useWebSocket;
