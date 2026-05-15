import json
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from jose import JWTError

from app.services.auth_service import decode_token

router = APIRouter(tags=["realtime"])

# In-memory connection registry (replace with Redis broadcaster for multi-node)
_connections: Dict[str, List[WebSocket]] = {}


async def _authenticate_ws(token: str) -> str:
    """Returns user_id from JWT or raises ValueError."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Invalid token type")
        return payload["sub"]
    except JWTError:
        raise ValueError("Invalid token")


@router.websocket("/ws/attempts/{attempt_id}")
async def attempt_ws(
    websocket: WebSocket,
    attempt_id: str,
    token: str = Query(...),
):
    try:
        user_id = await _authenticate_ws(token)
    except ValueError:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    if attempt_id not in _connections:
        _connections[attempt_id] = []
    _connections[attempt_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg["from"] = user_id
            # Broadcast to all connections in this attempt room
            dead = []
            for conn in _connections.get(attempt_id, []):
                try:
                    await conn.send_text(json.dumps(msg))
                except Exception:
                    dead.append(conn)
            for d in dead:
                _connections[attempt_id].remove(d)
    except WebSocketDisconnect:
        if attempt_id in _connections and websocket in _connections[attempt_id]:
            _connections[attempt_id].remove(websocket)


async def broadcast_to_attempt(attempt_id: str, event: dict) -> None:
    """Utility used by other services to push events to connected clients."""
    dead = []
    for conn in _connections.get(attempt_id, []):
        try:
            await conn.send_text(json.dumps(event))
        except Exception:
            dead.append(conn)
    for d in dead:
        _connections[attempt_id].remove(d)
