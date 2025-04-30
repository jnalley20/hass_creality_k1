"""DataUpdateCoordinator for the Creality K1 integration."""
import asyncio
import logging
from datetime import timedelta
import websockets  # Import websockets

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN
from .websocket import MyWebSocket  # MyWebSocket class from websockets.py

_LOGGER = logging.getLogger(__name__)

class CrealityK1DataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Creality K1."""

    def __init__(
        self,
        hass: HomeAssistant,
        websocket: MyWebSocket,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        self.websocket = websocket
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.latest_data = {}  # Store the processed data

    async def _async_update_data(self) -> dict:
        """Fetch data from Creality K1."""
        try:
            raw_data = await self.websocket.get_latest_data()
            _LOGGER.debug(f"Coordinator: Fetched raw data: {raw_data}")

            if raw_data:
                self.latest_data = self.process_raw_data(raw_data, self.latest_data)  # Process data
                _LOGGER.debug(f"Coordinator: Processed data: {self.latest_data}")
                _LOGGER.debug(f"Coordinator: lightSw value in processed_data: {self.latest_data.get('lightSw')}")
            return self.latest_data
        except websockets.exceptions.ConnectionClosedError as err:
            _LOGGER.warning("WebSocket connection closed, attempting to reconnect.")
            await self.websocket.connect()  # Försök att återansluta
            raise UpdateFailed(f"WebSocket connection closed: {err}") from err
        except Exception as err:
            _LOGGER.error(f"Error communicating with Creality K1: {err}")
            raise UpdateFailed(f"Error communicating with Creality K1: {err}") from err

    def process_raw_data(self, raw_data: dict, stored_data: dict) -> dict:
        """Process the raw data and return the combined dictionary."""
        # Skapa en kopia av den lagrade datan för att undvika sidoeffekter
        processed_data = stored_data.copy()
        # Uppdatera med den nya datan (nya värden skriver över gamla)
        processed_data.update(raw_data)
        # Returnera den kombinerade/uppdaterade datan
        return processed_data

    async def connect(self) -> None:
        """Connect to the printer."""
        _LOGGER.info("Connecting to Creality K1 printer.")
        await self.websocket.connect()

    async def disconnect(self) -> None:
        """Disconnect from the printer."""
        _LOGGER.info("Disconnecting from Creality K1 printer.")
        await self.websocket.clear()

    async def send_message(self, message: dict) -> None:
        """Send a message to the printer."""
        _LOGGER.debug(f"Sending message to printer: {message}")
        await self.websocket.send_message(message)