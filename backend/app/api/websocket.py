"""
websocket.py - Real-Time Updates via WebSocket
-----------------------------------------------

Provides WebSocket connections for real-time claim and trigger updates.

Features:
- Partner-specific WebSocket connections
- Real-time claim status updates
- Trigger alert broadcasts
- Connection management with auto-cleanup

Usage:
    Frontend: ws://localhost:8000/api/v1/ws/claims/{partner_id}

Events:
    - claim_update: Sent when claim status changes
    - trigger_alert: Sent when new trigger fires in partner's zone
    - heartbeat: Keep-alive ping
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json


router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """
    Manage WebSocket connections for real-time updates.

    Maintains a mapping of partner_id -> list of active WebSocket connections.
    Supports multiple connections per partner (e.g., mobile + desktop).
    """

    def __init__(self):
        # Map partner_id -> list of websocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, partner_id: int, websocket: WebSocket):
        """
        Accept new WebSocket connection for a partner.

        Args:
            partner_id: Partner ID to associate with this connection
            websocket: WebSocket connection object
        """
        await websocket.accept()

        if partner_id not in self.active_connections:
            self.active_connections[partner_id] = []

        self.active_connections[partner_id].append(websocket)
        print(f"[WebSocket] Partner {partner_id} connected (total: {len(self.active_connections[partner_id])})")

    def disconnect(self, partner_id: int, websocket: WebSocket):
        """
        Remove WebSocket connection from active connections.

        Args:
            partner_id: Partner ID
            websocket: WebSocket connection to remove
        """
        if partner_id in self.active_connections:
            try:
                self.active_connections[partner_id].remove(websocket)
                print(f"[WebSocket] Partner {partner_id} disconnected (remaining: {len(self.active_connections[partner_id])})")

                # Clean up empty lists
                if not self.active_connections[partner_id]:
                    del self.active_connections[partner_id]
            except ValueError:
                pass  # Already removed

    async def send_claim_update(self, partner_id: int, claim_data: dict):
        """
        Send claim update to all active connections for a partner.

        Args:
            partner_id: Partner ID
            claim_data: Claim data to send (includes claim_id, status, amount, etc.)

        Message Format:
            {
                "type": "claim_update",
                "data": {
                    "claim_id": 123,
                    "status": "approved",
                    "amount": 400,
                    "trigger_type": "rain",
                    "updated_at": "2026-04-17T17:00:00Z"
                }
            }
        """
        if partner_id not in self.active_connections:
            return  # No active connections for this partner

        message = {
            "type": "claim_update",
            "data": claim_data,
            "timestamp": claim_data.get("updated_at", "")
        }

        # Send to all partner's active connections
        dead_connections = []
        for connection in self.active_connections[partner_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[WebSocket] Failed to send to partner {partner_id}: {e}")
                dead_connections.append(connection)

        # Clean up dead connections
        for dead in dead_connections:
            self.disconnect(partner_id, dead)

    async def send_trigger_alert(self, zone_id: int, trigger_data: dict):
        """
        Broadcast trigger alert to all partners in a zone.

        Args:
            zone_id: Zone ID where trigger fired
            trigger_data: Trigger data (type, severity, started_at, etc.)

        Message Format:
            {
                "type": "trigger_alert",
                "data": {
                    "trigger_id": 456,
                    "zone_id": 1,
                    "trigger_type": "rain",
                    "severity": 3,
                    "started_at": "2026-04-17T17:00:00Z"
                }
            }

        Note:
            In production, filter by partner's active policy zone.
            For now, broadcasts to all connected partners.
        """
        message = {
            "type": "trigger_alert",
            "data": trigger_data,
            "timestamp": trigger_data.get("started_at", "")
        }

        # Broadcast to all connected partners
        # TODO: Filter by zone_id using partner's active policy
        for partner_id, connections in list(self.active_connections.items()):
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass  # Ignore errors on broadcast

    async def send_heartbeat(self, partner_id: int):
        """Send heartbeat to keep connection alive."""
        if partner_id not in self.active_connections:
            return

        message = {
            "type": "heartbeat",
            "status": "connected"
        }

        for connection in self.active_connections[partner_id]:
            try:
                await connection.send_json(message)
            except Exception:
                pass


# Singleton connection manager
manager = ConnectionManager()


@router.websocket("/claims/{partner_id}")
async def websocket_endpoint(websocket: WebSocket, partner_id: int):
    """
    WebSocket endpoint for real-time claim updates.

    URL: ws://localhost:8000/api/v1/ws/claims/{partner_id}

    Connection Flow:
        1. Client connects with partner_id
        2. Server accepts connection
        3. Server sends heartbeat every 30s
        4. Client can send messages (echoed back)
        5. Server sends claim_update when claims change
        6. Server sends trigger_alert when triggers fire

    Message Types:
        - claim_update: Claim status changed
        - trigger_alert: New trigger in partner's zone
        - heartbeat: Keep-alive ping

    Example Client (JavaScript):
        ```javascript
        const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/claims/${partnerId}`);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'claim_update') {
                console.log('Claim updated:', data.data);
                // Show notification to user
            } else if (data.type === 'trigger_alert') {
                console.log('New trigger:', data.data);
                // Alert user about new disruption event
            }
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
        };
        ```
    """
    await manager.connect(partner_id, websocket)

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()

            # Echo back as confirmation
            await websocket.send_json({
                "type": "echo",
                "message": data,
                "partner_id": partner_id
            })

            # Send heartbeat
            await manager.send_heartbeat(partner_id)

    except WebSocketDisconnect:
        manager.disconnect(partner_id, websocket)
        print(f"[WebSocket] Partner {partner_id} disconnected")


# Export manager for use in other modules
__all__ = ["router", "manager"]
