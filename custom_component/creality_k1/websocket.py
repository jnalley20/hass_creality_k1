"""WebSocket communication for Creality K1 Max."""
import asyncio
import websockets
import json
import logging
import time

from .const import DOMAIN, MSG_TYPE_MSG, MSG_TYPE_HEARTBEAT, HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT, RECONNECT_INTERVAL  # Om du har en const.py fil
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class MyWebSocket:
    """Handles WebSocket communication with the Creality K1 Max."""

    def __init__(self, url: str) -> None:
        """Initialize the WebSocket client."""
        self.url = url
        self.ws = None
        self.heartbeat_task = None
        self.receive_task = None
        self._is_connected = False
        self._latest_raw_data = {}  # Store the latest raw data

    async def init(self, hass: HomeAssistant) -> None:
        """Initialize the WebSocket connection and message handling."""
        self.hass = hass
        await self.connect()

    async def connect(self) -> None:
        """Connect to the WebSocket server and handle messages."""
        try:
            self.ws = await websockets.connect(self.url, ping_interval=None, ping_timeout=None)
            _LOGGER.info(f"Connected to {self.url}")
            self._is_connected = True
            self.heartbeat_task = asyncio.create_task(self.send_heartbeat())
            self.receive_task = asyncio.create_task(self.receive_messages())
        except Exception as e:
            _LOGGER.error(f"Connection failed: {e}")
            await self.reconnect()  # Försök återansluta direkt

    async def send_heartbeat(self) -> None:
        """Send a heartbeat message to the server periodically."""
        try:
            while self._is_connected:
                await self.send_message({"ModeCode": MSG_TYPE_HEARTBEAT, "msg": time.time()})
                await asyncio.sleep(HEARTBEAT_INTERVAL)
        except Exception as e:
            _LOGGER.error(f"Error sending heartbeat: {e}")
            await self.reconnect()

    async def receive_messages(self) -> None:
        """Receive and process messages from the WebSocket server."""
        try:
            while self._is_connected:
                try:
                    message = await self.ws.recv()
                    if message is None:
                        _LOGGER.warning("Received None message from server")
                        break  # Break the loop to reconnect
                    await self.handle_message(message)
                except websockets.exceptions.ConnectionClosedOK:
                    _LOGGER.info("Connection closed by server")
                    break  # Break the loop to reconnect
                except Exception as e:
                    _LOGGER.error(f"Error receiving message: {e}")
                    break  # Break the loop to reconnect
        finally:
            self._is_connected = False
            await self.reconnect()

    async def handle_message(self, message: str) -> None:
        """Process a received message."""
        # Log RAW data in DEBUG-mode
        _LOGGER.debug(f"Raw message received: {message}")

        if message.strip().lower() == "ok":
            _LOGGER.debug("Received 'ok' acknowledgment.")
            # We don't need to do anything more so we stop here
            return

        # If not "ok", try it as JSON
        try:
            data = json.loads(message)
            _LOGGER.debug(f"Received Parsed JSON: {data}") # Ändrat från Received:

            # Check if it is HEARTBEAT message
            if data.get("ModeCode") == MSG_TYPE_HEARTBEAT:
                _LOGGER.debug("Received heartbeat response")
                # We don't need to do anything with this data
                return

            # If it is JSON and not heartbeat, update stored data
            self._latest_raw_data.update(data)

        except json.JSONDecodeError:
            # Log if it is not JSON and not "ok" message
            _LOGGER.warning(f"Invalid JSON received (and not 'ok'): {message}")
        except Exception as e:
            _LOGGER.error(f"Error handling non-JSON message '{message}': {e}")

    async def send_message(self, message: dict) -> None:
        """Send a message to the WebSocket server."""
        try:
            if self.ws and self._is_connected:
                await self.ws.send(json.dumps(message))
                _LOGGER.debug(f"Sent: {message}")
            else:
                _LOGGER.warning("WebSocket connection is not active")
        except Exception as e:
            _LOGGER.error(f"Error sending message: {e}")
            await self.reconnect()

    async def reconnect(self) -> None:
        """Reconnect to the WebSocket server."""
        self._is_connected = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.receive_task:
            self.receive_task.cancel()

        _LOGGER.warning(f"Attempting to reconnect in {RECONNECT_INTERVAL} seconds...")
        await asyncio.sleep(RECONNECT_INTERVAL)
        await self.connect()

    async def clear(self) -> None:
        """Close the WebSocket connection and cleanup."""
        self._is_connected = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.receive_task:
            self.receive_task.cancel()
        if self.ws:
            await self.ws.close()
            self.ws = None
        _LOGGER.info("WebSocket connection closed.")

    async def get_latest_data(self) -> dict:
        """Get the latest received data."""
        return self._latest_raw_data