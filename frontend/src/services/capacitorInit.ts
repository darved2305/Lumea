/**
 * Capacitor App Initialization
 * Initializes native plugins and sets up global listeners for:
 * - Back button handling
 * - Network status changes
 * - App lifecycle (pause/resume)
 * - Splash screen
 */
import { App, BackButtonListenerEvent } from '@capacitor/app';
import { Network, ConnectionStatus } from '@capacitor/network';
import { SplashScreen } from '@capacitor/splash-screen';
import { StatusBar, Style } from '@capacitor/status-bar';
import { Capacitor } from '@capacitor/core';
import { initTokenCache } from './tokenService';

// Store the network status globally
let currentNetworkStatus: ConnectionStatus | null = null;
let networkListeners: ((status: ConnectionStatus) => void)[] = [];

/**
 * Initialize all Capacitor plugins and listeners
 * Call this once in your app's main entry point
 */
export async function initCapacitor(): Promise<void> {
    if (!Capacitor.isNativePlatform()) {
        console.log('[Capacitor] Running on web, skipping native initialization');
        return;
    }

    console.log('[Capacitor] Initializing native plugins...');

    try {
        // Initialize token cache for sync access
        await initTokenCache();

        // Configure status bar
        await StatusBar.setStyle({ style: Style.Light });
        await StatusBar.setBackgroundColor({ color: '#f5f0e8' }); // Lumea cream

        // Set up back button handler
        App.addListener('backButton', handleBackButton);

        // Set up network listener
        const status = await Network.getStatus();
        currentNetworkStatus = status;
        console.log('[Capacitor] Initial network status:', status.connected ? 'online' : 'offline');

        Network.addListener('networkStatusChange', (status) => {
            currentNetworkStatus = status;
            console.log('[Capacitor] Network status changed:', status.connected ? 'online' : 'offline');

            // Notify all subscribers
            networkListeners.forEach(listener => listener(status));

            // Dispatch custom event for components that listen
            window.dispatchEvent(new CustomEvent('networkStatusChange', { detail: status }));
        });

        // Set up app lifecycle listeners
        App.addListener('pause', () => {
            console.log('[Capacitor] App paused');
            window.dispatchEvent(new CustomEvent('appPause'));
        });

        App.addListener('resume', () => {
            console.log('[Capacitor] App resumed');
            window.dispatchEvent(new CustomEvent('appResume'));
        });

        // Handle restored result (e.g., from camera)
        App.addListener('appRestoredResult', (data) => {
            console.log('[Capacitor] App restored with result:', data);
            window.dispatchEvent(new CustomEvent('appRestoredResult', { detail: data }));
        });

        // Hide splash screen after initialization
        await SplashScreen.hide();

        console.log('[Capacitor] Native initialization complete');
    } catch (error) {
        console.error('[Capacitor] Initialization error:', error);
        // Still try to hide splash screen on error
        try {
            await SplashScreen.hide();
        } catch {
            // Ignore
        }
    }
}

/**
 * Handle Android back button
 */
function handleBackButton({ canGoBack }: BackButtonListenerEvent): void {
    if (canGoBack) {
        // Let the WebView handle navigation
        window.history.back();
    } else {
        // At the root of the app - confirm exit
        if (window.confirm('Exit Lumea?')) {
            App.exitApp();
        }
    }
}

/**
 * Get current network status
 */
export function getNetworkStatus(): ConnectionStatus | null {
    return currentNetworkStatus;
}

/**
 * Check if currently online
 */
export function isOnline(): boolean {
    if (!Capacitor.isNativePlatform()) {
        return navigator.onLine;
    }
    return currentNetworkStatus?.connected ?? true;
}

/**
 * Subscribe to network status changes
 */
export function onNetworkChange(callback: (status: ConnectionStatus) => void): () => void {
    networkListeners.push(callback);

    // Return unsubscribe function
    return () => {
        networkListeners = networkListeners.filter(l => l !== callback);
    };
}

export default {
    initCapacitor,
    getNetworkStatus,
    isOnline,
    onNetworkChange,
};
