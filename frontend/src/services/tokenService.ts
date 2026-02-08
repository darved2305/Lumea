/**
 * TokenService - Cross-platform token storage
 * Uses Capacitor Preferences (SharedPreferences on Android, UserDefaults on iOS)
 * Falls back to localStorage on web for development
 */
import { Preferences } from '@capacitor/preferences';
import { Capacitor } from '@capacitor/core';

const TOKEN_KEY = 'access_token';

/**
 * Check if running on native platform
 */
const isNative = (): boolean => {
    return Capacitor.isNativePlatform();
};

/**
 * Get the auth token
 * @returns Promise<string | null>
 */
export const getToken = async (): Promise<string | null> => {
    if (isNative()) {
        const { value } = await Preferences.get({ key: TOKEN_KEY });
        return value;
    }
    // Web fallback
    return localStorage.getItem(TOKEN_KEY);
};

/**
 * Set the auth token
 * @param token The token to store
 */
export const setToken = async (token: string): Promise<void> => {
    if (isNative()) {
        await Preferences.set({ key: TOKEN_KEY, value: token });
    } else {
        localStorage.setItem(TOKEN_KEY, token);
    }
    // Dispatch custom event for cross-component notification
    window.dispatchEvent(new CustomEvent('tokenChanged', { detail: { token } }));
};

/**
 * Remove the auth token (logout)
 */
export const removeToken = async (): Promise<void> => {
    if (isNative()) {
        await Preferences.remove({ key: TOKEN_KEY });
    } else {
        localStorage.removeItem(TOKEN_KEY);
    }
    window.dispatchEvent(new CustomEvent('tokenChanged', { detail: { token: null } }));
};

/**
 * Check if user is authenticated
 * @returns Promise<boolean>
 */
export const isAuthenticated = async (): Promise<boolean> => {
    const token = await getToken();
    return !!token;
};

/**
 * Get token synchronously (for web compatibility - returns cached value)
 * Use getToken() for native platforms
 */
let cachedToken: string | null = null;

export const getTokenSync = (): string | null => {
    if (!isNative()) {
        return localStorage.getItem(TOKEN_KEY);
    }
    return cachedToken;
};

/**
 * Initialize token cache (call on app startup)
 */
export const initTokenCache = async (): Promise<void> => {
    cachedToken = await getToken();

    // Listen for token changes
    window.addEventListener('tokenChanged', (e: any) => {
        cachedToken = e.detail?.token || null;
    });
};

export default {
    getToken,
    setToken,
    removeToken,
    isAuthenticated,
    getTokenSync,
    initTokenCache,
};
