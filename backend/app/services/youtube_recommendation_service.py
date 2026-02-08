"""
YouTube Recommendation Service

Uses OpenRouter API to generate contextual YouTube video recommendations
based on organ telemetry data and detected health conditions.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional
import httpx
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.settings import Settings

logger = logging.getLogger(__name__)


class YouTubeRecommendationService:
    """Generate accurate YouTube video recommendations for health improvement"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.openrouter_api_key = settings.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")
        self.youtube_api_key = settings.google_places_api_key or os.getenv("YOUTUBE_API_KEY")
        
        if not self.openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY not configured - YouTube recommendations will use fallback")
        
        self.openrouter_base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.timeout = 30

    async def generate_recommendations(
        self,
        organ: str,
        score: float,
        status: str,
        metrics: Dict[str, float],
        conditions: List[Dict],
    ) -> List[Dict[str, str]]:
        """
        Generate YouTube video recommendations based on organ health data.
        
        Args:
            organ: Organ name (e.g., "kidney", "heart", "liver")
            score: Organ health score (0-100)
            status: Health status ("Healthy", "Watch", "Risk")
            metrics: Current metric values affecting this organ
            conditions: List of detected conditions affecting this organ
            
        Returns:
            List of video recommendations with title, videoId, thumbnail, and description
        """
        try:
            # Generate search queries using OpenRouter
            queries = await self._generate_search_queries(organ, score, status, metrics, conditions)
            
            # Fetch actual YouTube videos for each query
            recommendations = []
            for query in queries[:3]:  # Limit to top 3 queries to save API calls
                videos = await self._search_youtube(query)
                if videos:
                    recommendations.extend(videos[:2])  # Top 2 videos per query
            
            # Deduplicate by video ID and limit to 5 total
            seen_ids = set()
            unique_recommendations = []
            for video in recommendations:
                if video["videoId"] not in seen_ids:
                    seen_ids.add(video["videoId"])
                    unique_recommendations.append(video)
                if len(unique_recommendations) >= 5:
                    break
            
            return unique_recommendations
        
        except Exception as e:
            logger.exception(f"Error generating YouTube recommendations: {e}")
            return self._get_fallback_recommendations(organ, conditions)

    async def _generate_search_queries(
        self,
        organ: str,
        score: float,
        status: str,
        metrics: Dict[str, float],
        conditions: List[Dict],
    ) -> List[str]:
        """Use OpenRouter AI to generate targeted YouTube search queries"""
        
        if not self.openrouter_api_key:
            return self._get_fallback_queries(organ, conditions)
        
        # Build context for AI
        condition_text = ""
        if conditions:
            condition_names = [c.get("name", "") for c in conditions]
            condition_text = f"Detected conditions: {', '.join(condition_names)}. "
        
        metric_text = ""
        if metrics:
            metric_items = [f"{k.replace('_', ' ')}: {v:.1f}" for k, v in metrics.items()]
            metric_text = f"Key metrics: {', '.join(metric_items)}. "
        
        prompt = f"""You are a medical health educator. Generate 5 specific, actionable YouTube search queries for someone with:

Organ: {organ.upper()}
Health Score: {score:.1f}/100 ({status})
{condition_text}{metric_text}

Requirements:
1. Each query should target EVIDENCE-BASED educational content
2. Focus on practical improvement strategies, diet, exercise, lifestyle
3. Include specific terms like "doctor explains", "Mayo Clinic", "medical review"
4. Avoid clickbait - prioritize credible medical sources
5. Mix general organ health with specific condition management

Return ONLY the 5 search queries, one per line, no numbering or extra text."""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.openrouter_base_url,
                    headers={
                        "Authorization": f"Bearer {self.openrouter_api_key}",
                        "HTTP-Referer": "https://lumea-health.com",
                        "X-Title": "Lumea Health YouTube Recommendations",
                    },
                    json={
                        "model": "openai/gpt-4o-mini",  # Fast and accurate
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 300,
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    queries = [q.strip() for q in content.strip().split("\n") if q.strip()]
                    logger.info(f"Generated {len(queries)} queries for {organ}: {queries}")
                    return queries[:5]
                else:
                    logger.warning(f"OpenRouter returned status {response.status_code}")
                    return self._get_fallback_queries(organ, conditions)
        
        except Exception as e:
            logger.warning(f"Error calling OpenRouter: {e}")
            return self._get_fallback_queries(organ, conditions)

    async def _search_youtube(self, query: str) -> List[Dict[str, str]]:
        """Search YouTube Data API v3 for videos matching the query"""
        
        # Return search URL fallback if no API key - with generic placeholder
        if not self.youtube_api_key:
            logger.info(f"No YouTube API key - returning search link for: {query}")
            # Generate a more deterministic video ID for better caching
            video_id = f"srch{abs(hash(query)) % 1000000}"
            return [{
                "title": query,
                "videoId": video_id,
                "thumbnail": f"https://via.placeholder.com/320x180/6b9175/ffffff?text={query[:30].replace(' ', '+')}",
                "description": "Click to search YouTube for medical videos on this topic",
                "url": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}",
                "channelTitle": "YouTube Search"
            }]
        
        try:
            youtube = build("youtube", "v3", developerKey=self.youtube_api_key)
            
            search_response = youtube.search().list(
                q=query,
                part="id,snippet",
                maxResults=3,
                type="video",
                order="relevance",
                videoDuration="medium",  # 4-20 minutes
                videoDefinition="high",
                relevanceLanguage="en",
            ).execute()
            
            videos = []
            for item in search_response.get("items", []):
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]
                
                videos.append({
                    "title": snippet["title"],
                    "videoId": video_id,
                    "thumbnail": snippet["thumbnails"].get("medium", {}).get("url", ""),
                    "description": snippet["description"][:150] + "..." if len(snippet["description"]) > 150 else snippet["description"],
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "channelTitle": snippet["channelTitle"]
                })
            
            return videos
        
        except HttpError as e:
            logger.warning(f"YouTube API error for query '{query}': {e}")
            # Return search URL fallback with generic placeholder
            video_id = f"srch{abs(hash(query)) % 1000000}"
            return [{
                "title": query,
                "videoId": video_id,
                "thumbnail": f"https://via.placeholder.com/320x180/6b9175/ffffff?text={query[:30].replace(' ', '+')}",
                "description": "Click to search YouTube for medical videos on this topic",
                "url": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}",
                "channelTitle": "YouTube Search"
            }]
        
        except Exception as e:
            logger.exception(f"Error searching YouTube: {e}")
            return []

    def _get_fallback_queries(self, organ: str, conditions: List[Dict]) -> List[str]:
        """Fallback queries when AI is unavailable"""
        
        base_queries = {
            "kidney": [
                "how to improve kidney function naturally doctor explains",
                "kidney disease prevention Mayo Clinic",
                "best foods for kidney health medical review",
                "kidney health exercises and lifestyle changes",
                "understanding kidney function tests explained",
            ],
            "heart": [
                "heart health improvement doctor guide",
                "cardiovascular disease prevention explained",
                "best diet for heart health evidence based",
                "heart disease risk factors medical review",
                "improving heart health naturally Cleveland Clinic",
            ],
            "liver": [
                "liver health improvement natural methods",
                "fatty liver disease treatment explained",
                "liver detox what actually works doctor",
                "liver function tests explained medical",
                "best diet for liver health evidence based",
            ],
            "lungs": [
                "lung health improvement breathing exercises",
                "respiratory health doctor explains",
                "lung function improvement natural methods",
                "breathing techniques for better lung health",
                "pulmonary health prevention medical review",
            ],
            "brain": [
                "brain health improvement neuroplasticity",
                "cognitive function optimization doctor",
                "neurological health prevention methods",
                "brain health diet and lifestyle medical",
                "memory improvement techniques evidence based",
            ],
            "blood": [
                "blood health optimization complete guide",
                "anemia treatment natural methods doctor",
                "improving blood test results naturally",
                "hematology basics medical explanation",
                "blood health diet and supplements",
            ],
        }
        
        # Get base queries for organ
        queries = base_queries.get(organ.lower(), [
            f"{organ} health improvement doctor explains",
            f"how to improve {organ} function naturally",
            f"{organ} disease prevention medical review",
            f"best diet for {organ} health evidence based",
            f"{organ} health lifestyle changes doctor guide",
        ])
        
        # Add condition-specific queries
        if conditions:
            for condition in conditions[:2]:  # Top 2 conditions
                condition_name = condition.get("name", "")
                if condition_name:
                    queries.append(f"{condition_name} treatment explained doctor")
        
        return queries[:5]

    def _get_fallback_recommendations(self, organ: str, conditions: List[Dict]) -> List[Dict[str, str]]:
        """Static fallback when all APIs fail"""
        
        queries = self._get_fallback_queries(organ, conditions)
        
        return [{
            "title": query,
            "videoId": f"fallback_{i}_{abs(hash(query)) % 1000}",
            "thumbnail": f"https://via.placeholder.com/320x180/6b9175/ffffff?text={query[:30].replace(' ', '+')}",
            "description": "Click to search YouTube for medical videos on this topic",
            "url": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}",
            "channelTitle": "YouTube Search"
        } for i, query in enumerate(queries)]
