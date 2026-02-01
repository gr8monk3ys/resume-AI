"""
WebSocket router for real-time job alert notifications.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.database import SessionLocal
from app.middleware.auth import decode_token
from app.models.user import User
from app.services.job_alerts import get_job_alert_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    Manages WebSocket connections for real-time notifications.

    Handles connection lifecycle, message broadcasting, and
    user-specific notifications.
    """

    def __init__(self):
        """Initialize the connection manager."""
        # Map user_id to set of WebSocket connections (supports multiple tabs/devices)
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Map WebSocket to user_id for quick lookup
        self.connection_users: Dict[WebSocket, int] = {}
        # Keepalive interval in seconds
        self.keepalive_interval = 30

    async def connect(self, websocket: WebSocket, user_id: int) -> bool:
        """
        Accept a WebSocket connection and register it.

        Args:
            websocket: The WebSocket connection
            user_id: The authenticated user's ID

        Returns:
            True if connection was successful
        """
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id

        logger.info(f"WebSocket connected for user {user_id}")
        return True

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
        """
        user_id = self.connection_users.get(websocket)
        if user_id is not None:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            del self.connection_users[websocket]
            logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: dict, user_id: int):
        """
        Send a message to all connections for a specific user.

        Args:
            message: The message to send
            user_id: The target user's ID
        """
        if user_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send message to user {user_id}: {e}")
                    dead_connections.add(connection)

            # Clean up dead connections
            for conn in dead_connections:
                self.disconnect(conn)

    async def broadcast(self, message: dict):
        """
        Broadcast a message to all connected users.

        Args:
            message: The message to broadcast
        """
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)

    def get_connection_count(self, user_id: int = None) -> int:
        """
        Get the number of active connections.

        Args:
            user_id: If provided, return count for specific user

        Returns:
            Number of active connections
        """
        if user_id is not None:
            return len(self.active_connections.get(user_id, set()))
        return sum(len(conns) for conns in self.active_connections.values())

    def is_user_connected(self, user_id: int) -> bool:
        """
        Check if a user has any active connections.

        Args:
            user_id: The user's ID

        Returns:
            True if the user has at least one connection
        """
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


# Global connection manager instance
manager = ConnectionManager()


async def authenticate_websocket(
    websocket: WebSocket, token: str = None
) -> tuple[bool, int | None, str | None]:
    """
    Authenticate a WebSocket connection using JWT token.

    Args:
        websocket: The WebSocket connection
        token: The JWT token

    Returns:
        Tuple of (is_authenticated, user_id, error_message)

    Security:
        - Validates token signature and expiration
        - Validates token type must be "access" (rejects refresh tokens)
        - Validates token_version matches user's current token_version
          (ensures tokens are invalidated after password change)
    """
    if not token:
        return False, None, "Authentication token required"

    # Decode token with type validation (must be access token, not refresh)
    token_data = decode_token(token, expected_type="access", validate_type=True)
    if token_data is None:
        return False, None, "Invalid or expired token"

    # Verify user exists and is active
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user:
            return False, None, "User not found"
        if not user.is_active:
            return False, None, "User account is deactivated"

        # Validate token version to ensure token hasn't been invalidated
        # This catches tokens issued before a password change
        if token_data.token_version != user.token_version:
            return False, None, "Token has been invalidated. Please log in again."

        return True, user.id, None
    finally:
        db.close()


async def check_alerts_for_user(user_id: int):
    """
    Check alerts for a specific user and send notifications.

    Args:
        user_id: The user's ID
    """
    db = SessionLocal()
    try:
        service = get_job_alert_service(db)
        notifications = service.check_alerts(user_id)

        for notification in notifications:
            message = {
                "type": "notification",
                "data": notification.model_dump(),
                "timestamp": datetime.utcnow().isoformat(),
            }
            await manager.send_personal_message(message, user_id)
    except Exception as e:
        logger.error(f"Error checking alerts for user {user_id}: {e}")
    finally:
        db.close()


@router.websocket("/ws/alerts/{user_id}")
async def websocket_alerts_endpoint(
    websocket: WebSocket,
    user_id: int,
):
    """
    WebSocket endpoint for real-time job alert notifications.

    Connect to receive instant notifications when new jobs match your alerts.

    Authentication:
        After connection, send an auth message: {"type": "auth", "token": "<jwt_token>"}
        The server will close the connection if authentication fails or times out.

    Messages from server:
        - notification: New jobs match an alert
        - pong: Response to ping (keepalive)
        - error: Error message
        - connected: Connection established (after successful auth)
        - auth_required: Sent immediately after connection, prompts for auth message

    Messages to server:
        - auth: Authentication message with JWT token (required first)
        - ping: Request pong response (keepalive)
        - check: Manually trigger alert check

    Args:
        websocket: The WebSocket connection
        user_id: The user's ID (must match token)
    """
    # Accept connection first, then wait for auth message
    await websocket.accept()

    # Send auth required message
    await websocket.send_json(
        {
            "type": "auth_required",
            "data": {"message": "Send auth message with token"},
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    # Wait for auth message with timeout (30 seconds)
    try:
        auth_data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
        auth_message = json.loads(auth_data)

        if auth_message.get("type") != "auth" or "token" not in auth_message:
            await websocket.send_json(
                {
                    "type": "error",
                    "data": {
                        "message": 'Invalid auth message. Expected: {"type": "auth", "token": "..."}'
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Invalid auth message"
            )
            return

        token = auth_message["token"]
    except asyncio.TimeoutError:
        await websocket.send_json(
            {
                "type": "error",
                "data": {"message": "Authentication timeout"},
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication timeout")
        return
    except json.JSONDecodeError:
        await websocket.send_json(
            {
                "type": "error",
                "data": {"message": "Invalid JSON in auth message"},
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid JSON")
        return

    # Authenticate using the token from the message
    is_authenticated, authenticated_user_id, error = await authenticate_websocket(websocket, token)

    if not is_authenticated:
        await websocket.send_json(
            {
                "type": "error",
                "data": {"message": error},
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=error)
        return

    # Verify user_id in URL matches authenticated user
    if authenticated_user_id != user_id:
        await websocket.send_json(
            {
                "type": "error",
                "data": {"message": "User ID mismatch"},
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="User ID mismatch",
        )
        return

    # Register connection with manager (already accepted above)
    if user_id not in manager.active_connections:
        manager.active_connections[user_id] = set()
    manager.active_connections[user_id].add(websocket)
    manager.connection_users[websocket] = user_id
    logger.info(f"WebSocket authenticated and connected for user {user_id}")

    # Send connection confirmation
    await websocket.send_json(
        {
            "type": "connected",
            "data": {
                "user_id": user_id,
                "message": "Connected to job alerts WebSocket",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    # Start keepalive task
    async def keepalive():
        """Send periodic ping to keep connection alive."""
        while True:
            try:
                await asyncio.sleep(manager.keepalive_interval)
                if not manager.is_user_connected(user_id):
                    break
                # Server-initiated ping
                await websocket.send_json(
                    {
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            except Exception:
                break

    keepalive_task = asyncio.create_task(keepalive())

    try:
        # Initial alert check on connect
        await check_alerts_for_user(user_id)

        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                message_type = message.get("type", "")

                if message_type == "ping":
                    # Respond to client ping with pong
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                elif message_type == "pong":
                    # Client responded to our ping - connection is alive
                    pass

                elif message_type == "check":
                    # Manual alert check requested
                    await check_alerts_for_user(user_id)

                else:
                    # Unknown message type
                    await websocket.send_json(
                        {
                            "type": "error",
                            "data": {"message": f"Unknown message type: {message_type}"},
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "data": {"message": "Invalid JSON message"},
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        keepalive_task.cancel()
        manager.disconnect(websocket)


@router.get("/ws/status")
async def websocket_status():
    """
    Get WebSocket connection status.

    Returns:
        Connection statistics
    """
    return {
        "total_connections": manager.get_connection_count(),
        "active_users": len(manager.active_connections),
    }


# Function to send notification to a user from anywhere in the application
async def notify_user(user_id: int, notification_type: str, data: dict):
    """
    Send a notification to a specific user.

    This can be called from anywhere in the application to send
    real-time notifications to connected users.

    Args:
        user_id: The target user's ID
        notification_type: Type of notification
        data: Notification data
    """
    message = {
        "type": notification_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }
    await manager.send_personal_message(message, user_id)
