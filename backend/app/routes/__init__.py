"""
Routes module for the Co-Code GGW Health Platform API.
"""
from . import auth, health, dashboard, reports, assistant, recommendations, websocket, ai_summary

__all__ = ['auth', 'health', 'dashboard', 'reports', 'assistant', 'recommendations', 'websocket', 'ai_summary']