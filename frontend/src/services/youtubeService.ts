/**
 * YouTube Data API v3 Service
 * Fetches real video data with thumbnails
 */

export interface YouTubeVideo {
  videoId: string;
  title: string;
  channelTitle: string;
  publishedAt: string;
  thumbnailUrl: string;
  url: string;
  description: string;
}

interface YouTubeSearchResponse {
  items: Array<{
    id: { videoId: string };
    snippet: {
      title: string;
      channelTitle: string;
      publishedAt: string;
      thumbnails: {
        default?: { url: string };
        medium?: { url: string };
        high?: { url: string };
      };
      description: string;
    };
  }>;
}

const YOUTUBE_API_KEY = import.meta.env.VITE_YOUTUBE_API_KEY;
const YOUTUBE_API_BASE = 'https://www.googleapis.com/youtube/v3';

export async function searchYouTubeVideos(query: string): Promise<YouTubeVideo[]> {
  if (!YOUTUBE_API_KEY) {
    console.warn('YouTube API key not configured');
    // Return placeholder data that opens YouTube search
    return [{
      videoId: 'placeholder',
      title: query,
      channelTitle: 'Search YouTube',
      publishedAt: new Date().toISOString(),
      thumbnailUrl: '',
      url: `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`,
      description: 'Click to search YouTube for this topic',
    }];
  }

  try {
    const params = new URLSearchParams({
      part: 'snippet',
      type: 'video',
      maxResults: '6',
      videoEmbeddable: 'true',
      safeSearch: 'strict',
      relevanceLanguage: 'en',
      q: query,
      key: YOUTUBE_API_KEY,
    });

    const response = await fetch(`${YOUTUBE_API_BASE}/search?${params}`);
    
    if (!response.ok) {
      throw new Error(`YouTube API error: ${response.statusText}`);
    }

    const data: YouTubeSearchResponse = await response.json();

    return data.items.map(item => {
      const thumbnails = item.snippet.thumbnails;
      const thumbnailUrl = 
        thumbnails.medium?.url || 
        thumbnails.high?.url || 
        thumbnails.default?.url || 
        '';

      return {
        videoId: item.id.videoId,
        title: item.snippet.title,
        channelTitle: item.snippet.channelTitle,
        publishedAt: item.snippet.publishedAt,
        thumbnailUrl,
        url: `https://www.youtube.com/watch?v=${item.id.videoId}`,
        description: item.snippet.description,
      };
    });
  } catch (error) {
    console.error('Error fetching YouTube videos:', error);
    throw error;
  }
}

export function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  const years = Math.floor(months / 12);
  return `${years}y ago`;
}
