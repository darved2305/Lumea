"""
Routes module for the Lumea Health Platform API.
"""
from . import auth, health, dashboard, reports, assistant, recommendations, websocket

__all__ = ['auth', 'health', 'dashboard', 'reports', 'assistant', 'recommendations', 'websocket']
