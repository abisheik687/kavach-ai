"""
<<<<<<< HEAD
KAVACH-AI WebSocket API Endpoints
=======
Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques WebSocket API Endpoints
>>>>>>> 7df14d1 (UI enhanced)
Real-time communication for alerts and detections
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from backend.alerts import get_alert_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Clients connect here to receive:
    - Detection events
    - Alert notifications
    - Stream status updates
    """
    alert_manager = get_alert_manager()
    await alert_manager.connection_manager.connect(websocket)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            'type': 'connected',
<<<<<<< HEAD
            'message': 'Connected to KAVACH-AI real-time updates'
=======
            'message': 'Connected to Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques real-time updates'
>>>>>>> 7df14d1 (UI enhanced)
        })
        
        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_json()
            
            # Handle client messages (ping, subscribe, etc.)
            if data.get('type') == 'ping':
                await websocket.send_json({'type': 'pong'})
            
    except WebSocketDisconnect:
        alert_manager.connection_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        alert_manager.connection_manager.disconnect(websocket)
