"""
Services module for the Co-Code GGW Health Platform.
"""
from .recommendation_service import RecommendationService, get_user_recommendations

__all__ = ['RecommendationService', 'get_user_recommendations']
