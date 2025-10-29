from fastapi import WebSocket
from typing import List, Dict, Optional
from datetime import datetime
import asyncio

class ConnectionManager:
    """
    Manages WebSocket connections for real-time meeting transcription.
    Handles connection tracking, session management, and broadcasting.
    Supports mobile voice recording with VAD-based chunking.
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # Track which session each connection is associated with
        self.connection_sessions: Dict[WebSocket, int] = {}
        # Track active recording sessions
        self.active_sessions: Dict[int, dict] = {}
    
    async def connect(self, websocket: WebSocket, session_id: Optional[int] = None):
        """Accept and track a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if session_id:
            self.connection_sessions[websocket] = session_id
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = {
                    "start_time": datetime.utcnow(),
                    "segment_count": 0,
                    "connections": []
                }
            self.active_sessions[session_id]["connections"].append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection from tracking."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Clean up session tracking
        if websocket in self.connection_sessions:
            session_id = self.connection_sessions[websocket]
            if session_id in self.active_sessions:
                if websocket in self.active_sessions[session_id]["connections"]:
                    self.active_sessions[session_id]["connections"].remove(websocket)
                # Remove session if no more connections
                if not self.active_sessions[session_id]["connections"]:
                    del self.active_sessions[session_id]
            del self.connection_sessions[websocket]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        await websocket.send_text(message)
    
    async def send_personal_json(self, data: dict, websocket: WebSocket):
        """Send JSON data to a specific WebSocket connection."""
        await websocket.send_json(data)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all active connections."""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
    
    async def broadcast_json(self, data: dict):
        """Broadcast JSON data to all active connections."""
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                print(f"Error broadcasting JSON to connection: {e}")
    
    async def broadcast_to_session(self, session_id: int, data: dict):
        """Broadcast to all connections in a specific session."""
        if session_id in self.active_sessions:
            connections = self.active_sessions[session_id]["connections"]
            for connection in connections:
                try:
                    await connection.send_json(data)
                except Exception as e:
                    print(f"Error broadcasting to session {session_id}: {e}")
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_active_sessions_count(self) -> int:
        """Get the number of active recording sessions."""
        return len(self.active_sessions)
    
    def increment_segment_count(self, session_id: int):
        """Increment segment counter for a session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["segment_count"] += 1
            return self.active_sessions[session_id]["segment_count"]
        return 0
    
    def get_session_info(self, session_id: int) -> Optional[dict]:
        """Get information about an active session."""
        return self.active_sessions.get(session_id)
