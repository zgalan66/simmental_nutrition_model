\
from fastapi import APIRouter, WebSocket
router = APIRouter()
@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "connected"})
