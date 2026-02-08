/**
 * Cross-platform Speech Recognition Service
 * Uses @capgo/capacitor-speech-recognition on native, Web Speech API on web
 */
import { Capacitor } from '@capacitor/core';
import { SpeechRecognition } from '@capgo/capacitor-speech-recognition';

export interface SpeechRecognitionResult {
    transcript: string;
    isFinal: boolean;
}

export interface SpeechRecognitionOptions {
    language?: string;
    onResult?: (result: SpeechRecognitionResult) => void;
    onError?: (error: string) => void;
    onEnd?: () => void;
}

// Store listener cleanup function
let partialResultsListener: { remove: () => void } | null = null;
let currentOptions: SpeechRecognitionOptions | null = null;

// Web Speech API instance
let webRecognition: any = null;

/**
 * Check if speech recognition is available
 */
export async function isAvailable(): Promise<boolean> {
    if (Capacitor.isNativePlatform()) {
        try {
            const result = await SpeechRecognition.available();
            return result.available;
        } catch {
            return false;
        }
    }

    // Web fallback
    const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    return !!SpeechRecognitionAPI;
}

/**
 * Request microphone permission
 */
export async function requestPermission(): Promise<boolean> {
    if (Capacitor.isNativePlatform()) {
        try {
            const result = await SpeechRecognition.requestPermissions();
            return result.speechRecognition === 'granted';
        } catch (error) {
            console.error('[SpeechService] Permission request failed:', error);
            return false;
        }
    }

    // Web fallback - request via getUserMedia
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());
        return true;
    } catch {
        return false;
    }
}

/**
 * Check current permission status
 */
export async function checkPermission(): Promise<'granted' | 'denied' | 'prompt'> {
    if (Capacitor.isNativePlatform()) {
        try {
            const result = await SpeechRecognition.checkPermissions();
            return result.speechRecognition as 'granted' | 'denied' | 'prompt';
        } catch {
            return 'denied';
        }
    }

    // Web fallback - check via permissions API
    try {
        const result = await navigator.permissions.query({ name: 'microphone' as PermissionName });
        return result.state as 'granted' | 'denied' | 'prompt';
    } catch {
        return 'prompt';
    }
}

/**
 * Get supported languages
 */
export async function getSupportedLanguages(): Promise<string[]> {
    if (Capacitor.isNativePlatform()) {
        try {
            const result = await SpeechRecognition.getSupportedLanguages();
            return result.languages || ['en-US'];
        } catch {
            return ['en-US'];
        }
    }

    // Common web speech languages
    return ['en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE', 'it-IT', 'pt-BR', 'ja-JP', 'ko-KR', 'zh-CN'];
}

/**
 * Start speech recognition
 */
export async function startListening(options: SpeechRecognitionOptions = {}): Promise<void> {
    currentOptions = options;
    const language = options.language || 'en-US';

    if (Capacitor.isNativePlatform()) {
        try {
            // Clean up any existing listener
            if (partialResultsListener) {
                partialResultsListener.remove();
                partialResultsListener = null;
            }

            // Set up partial results listener
            partialResultsListener = await SpeechRecognition.addListener('partialResults', (data: any) => {
                const matches = data.matches || [];
                if (matches.length > 0) {
                    currentOptions?.onResult?.({
                        transcript: matches[0],
                        isFinal: false,
                    });
                }
            });

            // Start recognition
            await SpeechRecognition.start({
                language,
                partialResults: true,
                popup: false,
            });

            console.log('[SpeechService] Native recognition started');
        } catch (error: any) {
            console.error('[SpeechService] Native start failed:', error);
            currentOptions?.onError?.(error.message || 'Failed to start speech recognition');
        }
    } else {
        // Web fallback
        const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

        if (!SpeechRecognitionAPI) {
            options.onError?.('Speech recognition not supported in this browser');
            return;
        }

        webRecognition = new SpeechRecognitionAPI();
        webRecognition.continuous = false;
        webRecognition.interimResults = true;
        webRecognition.lang = language;

        webRecognition.onresult = (event: any) => {
            const transcript = Array.from(event.results)
                .map((result: any) => result[0].transcript)
                .join('');

            const isFinal = event.results[event.results.length - 1].isFinal;

            currentOptions?.onResult?.({ transcript, isFinal });
        };

        webRecognition.onerror = (event: any) => {
            console.error('[SpeechService] Web recognition error:', event.error);
            if (event.error !== 'aborted') {
                currentOptions?.onError?.(event.error);
            }
        };

        webRecognition.onend = () => {
            currentOptions?.onEnd?.();
        };

        try {
            webRecognition.start();
            console.log('[SpeechService] Web recognition started');
        } catch (error: any) {
            currentOptions?.onError?.(error.message || 'Failed to start speech recognition');
        }
    }
}

/**
 * Stop speech recognition
 */
export async function stopListening(): Promise<string | null> {
    if (Capacitor.isNativePlatform()) {
        try {
            // Clean up listener
            if (partialResultsListener) {
                partialResultsListener.remove();
                partialResultsListener = null;
            }

            // @capgo/capacitor-speech-recognition stop() returns void
            // The last partialResults event already contains the final transcript
            await SpeechRecognition.stop();
            console.log('[SpeechService] Native recognition stopped');

            currentOptions?.onEnd?.();
            return null;
        } catch (error) {
            console.error('[SpeechService] Native stop failed:', error);
            currentOptions?.onEnd?.();
            return null;
        }
    } else {
        // Web fallback
        if (webRecognition) {
            try {
                webRecognition.stop();
                console.log('[SpeechService] Web recognition stopped');
            } catch (e) {
                // Ignore
            }
            webRecognition = null;
        }
        return null;
    }
}

/**
 * Abort speech recognition (don't process final result)
 */
export async function abortListening(): Promise<void> {
    if (Capacitor.isNativePlatform()) {
        if (partialResultsListener) {
            partialResultsListener.remove();
            partialResultsListener = null;
        }
        try {
            await SpeechRecognition.stop();
        } catch {
            // Ignore
        }
    } else {
        if (webRecognition) {
            try {
                webRecognition.abort();
            } catch {
                // Ignore
            }
            webRecognition = null;
        }
    }
    currentOptions = null;
}

export default {
    isAvailable,
    requestPermission,
    checkPermission,
    getSupportedLanguages,
    startListening,
    stopListening,
    abortListening,
};
