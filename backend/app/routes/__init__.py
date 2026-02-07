"""
Routes module for the Lumea Health Platform API.
"""
from . import auth, health, dashboard, reports, assistant, recommendations, websocket, ai_summary, medicines, memory, graph

__all__ = ['auth', 'health', 'dashboard', 'reports', 'assistant', 'recommendations', 'websocket', 'ai_summary', 'medicines', 'memory', 'graph']