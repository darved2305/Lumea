/**
 * Single source for API and WebSocket base URLs.
 * Uses VITE_API_URL so one env var works for both REST and WebSocket.
 */
const raw = typeof import.meta.env.VITE_API_URL === 'string' ? import.meta.env.VITE_API_URL.trim() : '';
const API_BASE_URL = raw ? raw.replace(/\/+$/, '') : 'http://localhost:8000';

/** WebSocket base URL derived from API URL (http -> ws, same host/port) */
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

export { API_BASE_URL, WS_BASE_URL };
