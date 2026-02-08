/**
 * OpenRouter Service
 * Uses AI to generate YouTube video recommendations based on health metrics.
 * NO YouTube API needed - generates video titles and search URLs directly.
 */

const OPENROUTER_API_KEY = import.meta.env.VITE_OPENROUTER_API_KEY || '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';
const OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1/chat/completions';

export interface AbnormalMetric {
  name: string;
  value: number;
  normalRange: string;
  status: 'high' | 'low';
}

export interface VideoRecommendation {
  title: string;
  description: string;
  url: string;
  duration: string;
}

export async function generateVideoRecommendations(
  organ: string,
  abnormalMetrics: AbnormalMetric[]
): Promise<VideoRecommendation[]> {
  // Use fallback if API not configured
  if (!OPENROUTER_API_KEY || OPENROUTER_API_KEY.includes('your_key')) {
    console.warn('OpenRouter API key not configured, using fallback recommendations');
    return generateFallbackRecommendations(organ, abnormalMetrics);
  }

  try {
    const prompt = buildPrompt(organ, abnormalMetrics);

    const response = await fetch(OPENROUTER_BASE_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': window.location.origin,
        'X-Title': 'Lumea Health - Physics Twin',
      },
      body: JSON.stringify({
        model: 'openai/gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: 'You are a health education expert. Generate 6 YouTube video recommendations with titles (max 60 chars), descriptions (max 100 chars), and search queries (5-8 words). Return ONLY valid JSON: {"videos":[{"title":"...","description":"...","searchQuery":"..."}]}',
          },
          {
            role: 'user',
            content: prompt,
          },
        ],
        temperature: 0.8,
        max_tokens: 1200,
      }),
    });

    if (!response.ok) {
      throw new Error(`OpenRouter API error: ${response.status}`);
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content?.trim() || '';

    if (content) {
      // Try to parse JSON response
      const parsed = JSON.parse(content);
      const videos = parsed.videos || [];
      
      if (Array.isArray(videos) && videos.length > 0) {
        return videos.slice(0, 6).map((v: any, index: number) => ({
          title: v.title || `${organ} Health Video ${index + 1}`,
          description: v.description || 'Learn how to improve your health naturally',
          url: `https://www.youtube.com/results?search_query=${encodeURIComponent(v.searchQuery || `${organ} health`)}`,
          duration: estimateDuration(v.searchQuery || ''),
        }));
      }
    }

    return generateFallbackRecommendations(organ, abnormalMetrics);
  } catch (error) {
    console.error('OpenRouter recommendation generation failed:', error);
    return generateFallbackRecommendations(organ, abnormalMetrics);
  }
}

function buildPrompt(organ: string, abnormalMetrics: AbnormalMetric[]): string {
  if (abnormalMetrics.length === 0) {
    return `Generate 6 YouTube video recommendations for improving ${organ} health. Include titles about: natural remedies, diet tips, exercises, lifestyle changes, supplements, and prevention. Make titles engaging and search queries specific.`;
  }

  const issues = abnormalMetrics
    .slice(0, 3)
    .map(m => `${m.name} is ${m.status} (normal: ${m.normalRange})`)
    .join(', ');

  return `Generate 6 YouTube video recommendations for ${organ} health when ${issues}. Include: diet changes, exercises, supplements, stress management, sleep tips, and medical advice. Make titles specific and actionable.`;
}

function generateFallbackRecommendations(organ: string, abnormalMetrics: AbnormalMetric[]): VideoRecommendation[] {
  const organLower = organ.toLowerCase();
  const topIssue = abnormalMetrics[0]?.name.toLowerCase() || 'health';
  
  return [
    {
      title: `How to Improve ${organ} Health Naturally`,
      description: 'Evidence-based tips for better organ function and overall wellness',
      url: `https://www.youtube.com/results?search_query=improve+${organLower}+health+naturally`,
      duration: '10-15 min',
    },
    {
      title: `Best Foods for ${organ} Health`,
      description: 'Nutritional guide for optimal function and disease prevention',
      url: `https://www.youtube.com/results?search_query=best+foods+for+${organLower}`,
      duration: '8-12 min',
    },
    {
      title: `${organ} Function: What You Need to Know`,
      description: 'Understanding how your organ works and signs of problems',
      url: `https://www.youtube.com/results?search_query=${organLower}+function+explained`,
      duration: '12-18 min',
    },
    {
      title: `Exercises for ${organ} Health`,
      description: 'Physical activities to support and improve organ function',
      url: `https://www.youtube.com/results?search_query=exercises+for+${organLower}+health`,
      duration: '15-20 min',
    },
    {
      title: `Managing ${topIssue} for Better ${organ} Health`,
      description: 'Targeted strategies for your specific health concerns',
      url: `https://www.youtube.com/results?search_query=${topIssue}+${organLower}+health`,
      duration: '10-15 min',
    },
    {
      title: `${organ} Health Supplements and Remedies`,
      description: 'Natural support options and what science says',
      url: `https://www.youtube.com/results?search_query=${organLower}+supplements+remedies`,
      duration: '8-12 min',
    },
  ];
}

function estimateDuration(searchQuery: string): string {
  // Estimate duration based on query complexity
  const words = searchQuery.split(' ').length;
  if (words <= 3) return '5-10 min';
  if (words <= 5) return '8-15 min';
  return '10-20 min';
}
