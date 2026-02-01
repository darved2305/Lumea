"""
WebSocket API for real-time updates

Replaces SSE with WebSocket for bidirectional communication.
"""
import json
import asyncio
from typing import Dict, Set
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.security import decode_access_token
from app.models import User
from sqlalchemy import select

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """
    Manages WebSocket connections per user.
    Supports multiple connections per user (multiple tabs/devices).
    """
    
    def __init__(self):
        # user_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections for a user"""
        if user_id not in self.active_connections:
            return
        
        dead_connections = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        
        # Clean up dead connections
        for conn in dead_connections:
            await self.disconnect(conn, user_id)
    
    async def broadcast_to_user(self, user_id: str, event_type: str, data: dict):
        """Broadcast an event to all user's connections"""
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(user_id, message)


# Global connection manager
manager = ConnectionManager()


async def get_user_from_token(token: str, db: AsyncSession) -> User | None:
    """Validate token and return user"""
    payload = decode_access_token(token)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None)  # Make token optional to handle gracefully
):
    """
    WebSocket endpoint for real-time updates.
    
    Connect with: ws://localhost:8000/ws?token=<jwt_token>
    
    Events sent to client:
    - report_processing_started: {report_id, progress}
    - report_parsed: {report_id, extracted_metrics_count}
    - health_index_updated: {score, breakdown, confidence, updated_at}
    - trends_updated: {metrics: [...]}
    - reports_list_updated: {}
    - recommendations_updated: {count, urgent_count}
    
    Events received from client:
    - ping: Client keepalive
    - subscribe: {topics: []} - Subscribe to specific event types
    """
    user_id = None
    
    # Validate token exists before attempting connection
    if not token:
        print("[WS] No token provided, rejecting connection")
        await websocket.close(code=4001, reason="No authentication token provided")
        return
    
    try:
        # Validate token and get user BEFORE accepting connection
        from app.db import async_session_maker
        
        # Create a dedicated session for this websocket
        async with async_session_maker() as db:
            user = await get_user_from_token(token, db)
            if not user:
                print(f"[WS] Invalid token, rejecting connection")
                await websocket.close(code=4001, reason="Invalid or expired token")
                return
            
            user_id = str(user.id)
        
        # Accept connection AFTER validation
        await manager.connect(websocket, user_id)
        
        print(f"WebSocket connected: user {user_id}")
        
        # Send connection established message
        await websocket.send_json({
            "type": "connected",
            "data": {"message": "WebSocket connected", "user_id": user_id},
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for message with timeout (keepalive ping)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # 60 second timeout - client pings every 25s
                )
                
                try:
                    message = json.loads(data)
                    msg_type = message.get("type")
                    
                    if msg_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    elif msg_type == "subscribe":
                        # Client can subscribe to specific topics
                        # For now, all events are sent to all connections
                        await websocket.send_json({
                            "type": "subscribed",
                            "data": {"topics": message.get("topics", [])},
                            "timestamp": datetime.utcnow().isoformat()
                        })
                
                except json.JSONDecodeError:
                    # Ignore malformed JSON
                    pass
                    
            except asyncio.TimeoutError:
                # Send keepalive ping from server side
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception:
                    # Connection is dead, break out
                    break
                    
    except WebSocketDisconnect as e:
        print(f"[WS] Disconnected: user {user_id}, code {e.code}")
    except Exception as e:
        print(f"[WS] Error for user {user_id}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        # Try to close gracefully with error code
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass
    finally:
        if user_id:
            await manager.disconnect(websocket, user_id)
            print(f"[WS] Cleaned up: user {user_id}")


# Helper functions to emit events (called from services/background tasks)
# These accept user_id to target specific users

async def emit_report_processing_started(user_id: str, data: dict):
    """Emit when report processing begins"""
    await manager.broadcast_to_user(str(user_id), "report_processing_started", data)


async def emit_report_parsed(user_id: str, data: dict):
    """Emit when report parsing completes"""
    await manager.broadcast_to_user(str(user_id), "report_parsed", data)


async def emit_health_index_updated(user_id: str, data: dict):
    """Emit when health index is recalculated"""
    data["updated_at"] = datetime.utcnow().isoformat()
    await manager.broadcast_to_user(str(user_id), "health_index_updated", data)


async def emit_trends_updated(user_id: str, data: dict):
    """Emit when trend data changes"""
    await manager.broadcast_to_user(str(user_id), "trends_updated", data)


async def emit_reports_list_updated(user_id: str):
    """Emit when reports list changes"""
    await manager.broadcast_to_user(str(user_id), "reports_list_updated", {})


async def emit_recommendations_updated(user_id: str, count: int, urgent_count: int = 0):
    """Emit when recommendations change"""
    await manager.broadcast_to_user(str(user_id), "recommendations_updated", {
        "count": count,
        "urgent_count": urgent_count
    })


async def emit_profile_updated(user_id: str):
    """Emit when profile is updated"""
    await manager.broadcast_to_user(str(user_id), "profile_updated", {
        "updated_at": datetime.utcnow().isoformat()
    })
