/**
 * Authentication utilities and route protection
 * Uses TokenService for cross-platform token storage (Capacitor Preferences on mobile)
 */
import { API_BASE_URL } from '../config/api';
import { getToken, setToken, removeToken, getTokenSync } from '../services/tokenService';

/**
 * Check if authenticated synchronously (for route guards)
 * Note: On mobile, this uses cached token value
 */
export const isAuthenticated = (): boolean => {
  const token = getTokenSync();
  return !!token;
};

/**
 * Check if authenticated asynchronously (preferred for mobile)
 */
export const isAuthenticatedAsync = async (): Promise<boolean> => {
  const token = await getToken();
  return !!token;
};

/**
 * Clear auth data
 */
export const clearAuth = async (): Promise<void> => {
  await removeToken();
  sessionStorage.clear();
};

/**
 * Get auth token synchronously (for headers in sync contexts)
 */
export const getAuthToken = (): string | null => {
  return getTokenSync();
};

/**
 * Get auth token asynchronously (preferred for mobile)
 */
export const getAuthTokenAsync = async (): Promise<string | null> => {
  return await getToken();
};

/**
 * Set auth token
 */
export const setAuthToken = async (token: string): Promise<void> => {
  await setToken(token);
};

/**
 * Logout - calls backend and clears local auth
 */
export const logout = async (): Promise<void> => {
  const token = await getToken();

  if (token) {
    try {
      // Call backend logout endpoint
      await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
    } catch (error) {
      console.error('Logout API call failed:', error);
      // Continue with local cleanup even if API call fails
    }
  }

  // Clear local auth data
  await clearAuth();
};
