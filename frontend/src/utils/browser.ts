/**
 * Cross-platform browser utility
 * Uses Capacitor Browser plugin on native, window.open on web
 */
import { Browser } from '@capacitor/browser';
import { Capacitor } from '@capacitor/core';

/**
 * Open a URL in the system browser
 * On mobile: uses native in-app browser
 * On web: uses window.open
 */
export const openUrl = async (url: string): Promise<void> => {
    if (Capacitor.isNativePlatform()) {
        await Browser.open({ url });
    } else {
        window.open(url, '_blank', 'noopener,noreferrer');
    }
};

/**
 * Open a URL for downloading (same as openUrl for now)
 * Future: could use Filesystem.downloadFile for more control
 */
export const openDownload = async (url: string): Promise<void> => {
    await openUrl(url);
};

export default { openUrl, openDownload };
