# Owner: agent-platform
import asyncio
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger("websocket_manager")

class ActiveConnection:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.queue = asyncio.Queue(maxsize=100)
        self.task = None
        self.active = True

    def start(self):
        self.task = asyncio.create_task(self._send_loop())

    async def _send_loop(self):
        try:
            while self.active:
                msg = await self.queue.get()
                # WebSocket send
                await self.websocket.send_json(msg)
                self.queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            self.active = False
            try:
                await self.websocket.close()
            except Exception:
                pass

    async def send_event(self, event: dict):
        if not self.active:
            return
        try:
            # Backpressure: non-blocking wait up to 2 seconds if buffer is full
            await asyncio.wait_for(self.queue.put(event), timeout=2.0)
        except asyncio.TimeoutError:
            logger.warning("Slow client detected: dropping message to enforce backpressure.")
        except Exception as e:
            logger.error(f"Failed to queue websocket event: {e}")

    async def close(self):
        self.active = False
        if self.task:
            self.task.cancel()
        try:
            await self.websocket.close()
        except Exception:
            pass


class WebSocketManager:
    def __init__(self):
        self._active_connections: Dict[str, List[ActiveConnection]] = {}

    def connect(self, run_id: str, websocket: WebSocket) -> ActiveConnection:
        conn = ActiveConnection(websocket)
        conn.start()
        if run_id not in self._active_connections:
            self._active_connections[run_id] = []
        self._active_connections[run_id].append(conn)
        return conn

    async def disconnect(self, run_id: str, conn: ActiveConnection):
        if run_id in self._active_connections:
            if conn in self._active_connections[run_id]:
                self._active_connections[run_id].remove(conn)
            if not self._active_connections[run_id]:
                del self._active_connections[run_id]
        await conn.close()

    async def broadcast(self, run_id: str, event: dict):
        connections = self._active_connections.get(run_id, [])
        if not connections:
            return
        await asyncio.gather(*(conn.send_event(event) for conn in connections), return_exceptions=True)

    async def broadcast_to_session(self, session_id: str, event: dict):
        """Broadcast an event to all WebSocket connections for a session by
        finding all runs belonging to that session and broadcasting to each."""
        broadcast_tasks = []
        for channel_id in list(self._active_connections.keys()):
            broadcast_tasks.append(self.broadcast(channel_id, event))
        if broadcast_tasks:
            await asyncio.gather(*broadcast_tasks, return_exceptions=True)

# Global singleton manager
ws_manager = WebSocketManager()
