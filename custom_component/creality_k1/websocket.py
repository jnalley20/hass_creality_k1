"""WebSocket communication for Creality K1 Max."""
import asyncio
import websockets
import json
import logging
import time

from .const import DOMAIN, MSG_TYPE_MSG, MSG_TYPE_HEARTBEAT, HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT, RECONNECT_INTERVAL  
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
        self._latest_raw_data = {}
        self.hass: HomeAssistant | None = None # Initialize hass
        self._reconnect_lock = asyncio.Lock() # To prevent concurrent reconnect attempts
        self._shutting_down = False # Flag to indicate intentional shutdown

    async def init(self, hass: HomeAssistant) -> None:
        """Initialize the WebSocket connection and message handling."""
        self.hass = hass
        self._shutting_down = False
        # Initial connection attempt. If it fails, reconnect logic will take over.
        await self.connect_and_start_tasks()

    async def connect_and_start_tasks(self) -> bool:
        """
        Attempts to connect and start heartbeat/receive tasks.
        This method will raise ConnectionError on failure to let the
        caller (e.g., async_setup_entry) handle the retry logic.
        """
        if self._is_connected:
            _LOGGER.debug("connect_and_start_tasks called but already connected.")
            return True
            
        if self._shutting_down:
            _LOGGER.info("WebSocket is shutting down, not attempting to connect.")
            return False

        try:
            # Ensure any old tasks or websocket connections are cleaned up
            # before attempting a new connection.
            await self._cleanup_connection_resources()

            _LOGGER.info(f"Attempting to connect to {self.url}...")
            # Add a timeout for the connection attempt itself to prevent it from hanging.
            self.ws = await asyncio.wait_for(
                websockets.connect(self.url, ping_interval=None, ping_timeout=None),
                timeout=10  # A 10-second timeout for the connection attempt.
            )
            
            _LOGGER.info(f"Successfully connected to {self.url}")
            self._is_connected = True
            
            # Start background tasks for heartbeat and receiving messages.
            self.heartbeat_task = asyncio.create_task(self._send_heartbeat_loop())
            self.receive_task = asyncio.create_task(self._receive_messages_loop())
            
            return True

        except (asyncio.TimeoutError, websockets.exceptions.WebSocketException, OSError) as e:
            # Catch specific, expected errors related to connection failure.
            _LOGGER.error(f"Failed to connect to {self.url}: {e} ({type(e).__name__})")
            self._is_connected = False
            
            # Raise an exception to let the calling function (in __init__.py)
            # know that the setup failed. This allows Home Assistant's core retry
            # mechanism to take over.
            raise ConnectionError(f"Failed to connect to WebSocket at {self.url}") from e
        
        except Exception as e:
            # Catch any other unexpected exceptions during connection.
            _LOGGER.error(f"An unexpected error occurred while connecting to {self.url}: {e}")
            self._is_connected = False
            raise ConnectionError(f"An unexpected error occurred connecting to WebSocket: {e}") from e


    async def _cleanup_connection_resources(self):
        """Safely cancel tasks and close websocket."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                _LOGGER.debug("Heartbeat task cancelled during cleanup.")
            except Exception as e: # Log other exceptions during task await
                _LOGGER.debug(f"Heartbeat task ended with exception during cleanup: {e}")
            self.heartbeat_task = None

        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                _LOGGER.debug("Receive task cancelled during cleanup.")
            except Exception as e: # Log other exceptions during task await
                _LOGGER.debug(f"Receive task ended with exception during cleanup: {e}")
            self.receive_task = None

        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                _LOGGER.debug(f"Error closing websocket during cleanup: {e}")
            self.ws = None
        self._is_connected = False


    async def _send_heartbeat_loop(self) -> None:
        """Send a heartbeat message to the server periodically."""
        try:
            while self._is_connected and not self._shutting_down:
                if not self.ws: # Should not happen if _is_connected is true
                    _LOGGER.warning("Heartbeat: WebSocket is None, though connected. Inconsistent state.")
                    break
                await self.send_message({"ModeCode": MSG_TYPE_HEARTBEAT, "msg": time.time()})
                await asyncio.sleep(HEARTBEAT_INTERVAL)
        except asyncio.CancelledError:
            _LOGGER.info("Heartbeat task was cancelled.")
        except websockets.exceptions.ConnectionClosed:
            _LOGGER.warning("Heartbeat: Connection closed while sending heartbeat.")
            self._handle_disconnect()
        except Exception as e:
            _LOGGER.error(f"Error in heartbeat loop: {e}")
            self._handle_disconnect()
        finally:
            _LOGGER.debug("Heartbeat task finished.")

    async def _receive_messages_loop(self) -> None:
        """Receive and process messages from the WebSocket server."""
        try:
            while self._is_connected and not self._shutting_down:
                if not self.ws: # Should not happen if _is_connected is true
                    _LOGGER.warning("Receive: WebSocket is None, though connected. Inconsistent state.")
                    break
                try:
                    # Add a timeout to ws.recv() to detect dead connections
                    message = await asyncio.wait_for(self.ws.recv(), timeout=HEARTBEAT_INTERVAL + HEARTBEAT_TIMEOUT)
                    if message is None:
                        _LOGGER.warning("Received None message from server. Assuming disconnection.")
                        self._handle_disconnect()
                        break
                    await self.handle_message(message)
                except asyncio.TimeoutError:
                    _LOGGER.warning("Timeout receiving message. Assuming connection lost.")
                    self._handle_disconnect()
                    break # Exit loop on timeout
                except websockets.exceptions.ConnectionClosedOK:
                    _LOGGER.info("Connection closed by server")
                    self._handle_disconnect()
                    break # Exit loop
                except websockets.exceptions.ConnectionClosedError as e:
                    _LOGGER.warning(f"Connection closed with error: {e}")
                    self._handle_disconnect()
                    break # Exit loop
                except Exception as e: # Catch other errors during recv or handle_message
                    _LOGGER.error(f"Error receiving/handling message: {e}")
                    self._handle_disconnect()
                    break # Exit loop
        except asyncio.CancelledError:
            _LOGGER.info("Receive messages task was cancelled.")
        finally:
            _LOGGER.debug("Receive messages task finished.")

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
        if not self._is_connected or not self.ws:
            _LOGGER.warning(f"WebSocket not connected. Cannot send: {message}")
            return

        try:
            await self.ws.send(json.dumps(message))
            _LOGGER.debug(f"Sent: {message}")
        except websockets.exceptions.ConnectionClosed:
            _LOGGER.error(f"Failed to send message, connection closed: {message}")
            self._handle_disconnect()
        except Exception as e:
            _LOGGER.error(f"Error sending message {message}: {e}")
            self._handle_disconnect()

    def _handle_disconnect(self):
        """Handles the disconnection sequence."""
        if self._is_connected: # If we thought we were connected
            _LOGGER.info("Handling disconnection.")
            self._is_connected = False # Mark as disconnected
            self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """Schedules a reconnect attempt if not already shutting down or reconnecting."""
        if self._shutting_down:
            _LOGGER.info("Shutdown in progress, not scheduling reconnect.")
            return

        if self.hass: # Ensure hass is available to create task
            _LOGGER.debug("Scheduling reconnect task.")
            asyncio.create_task(self._reconnect_cooldown_and_attempt())
        else:
            _LOGGER.error("HASS instance not available. Cannot schedule reconnect.")


    async def _reconnect_cooldown_and_attempt(self) -> None:
        """
        Waits for a cooldown, then enters a persistent loop
        to attempt reconnection until successful.
        """
        if self._shutting_down:
            return

        # Use the lock to ensure only one persistent reconnect loop runs at a time.
        async with self._reconnect_lock:
            # If another task managed to connect while we were waiting for the lock, abort.
            if self._is_connected:
                _LOGGER.debug("Already reconnected, skipping reconnect loop.")
                return

            _LOGGER.info("Starting persistent reconnection attempts...")
            while not self._is_connected and not self._shutting_down:
                try:
                    _LOGGER.debug("Executing reconnect attempt in loop.")
                    # connect_and_start_tasks will return True on success
                    # and raise ConnectionError on failure.
                    if await self.connect_and_start_tasks():
                        _LOGGER.info("Reconnection successful.")
                        # The _is_connected flag is now True, so the while loop will exit.
                        break
                except ConnectionError:
                    # This is expected if the printer is still offline/rebooting.
                    _LOGGER.warning(
                        f"Reconnect attempt failed. Retrying in {RECONNECT_INTERVAL} seconds..."
                    )
                except Exception as e:
                    # Catch any other unexpected errors to prevent the loop from crashing.
                    _LOGGER.error(f"Unexpected error during reconnect loop: {e}")

                # Wait before the next attempt in the loop.
                await asyncio.sleep(RECONNECT_INTERVAL)

            if self._shutting_down:
                _LOGGER.info("Shutdown initiated, stopping reconnect attempts.")
            
            _LOGGER.debug("Exited persistent reconnection loop.")

    async def clear(self) -> None:
        """Close the WebSocket connection and cleanup."""
        _LOGGER.info("Initiating WebSocket cleanup (clear).")
        self._shutting_down = True
        await self._cleanup_connection_resources()
        _LOGGER.info("WebSocket connection closed and cleaned up.")

    async def get_latest_data(self) -> dict:
        """Get the latest received data."""
        return self._latest_raw_data.copy()