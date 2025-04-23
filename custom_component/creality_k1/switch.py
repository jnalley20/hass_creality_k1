"""Platform for Creality K1 switches."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CrealityK1DataUpdateCoordinator  # DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Creality K1 switches."""
    coordinator: CrealityK1DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    websocket = hass.data[DOMAIN]["websocket"]  # Hämta WebSocket-klienten

    async_add_entities([
        K1LightSwitch(coordinator, websocket),
    #   K1ModelFanSwitch(coordinator, websocket),
    #   K1CaseFanSwitch(coordinator, websocket),
    #   K1AuxiliaryFanSwitch(coordinator, websocket),
    ])


class K1Switch(CoordinatorEntity, SwitchEntity):
    """Base class for Creality K1 switches."""

    def __init__(
        self,
        coordinator: CrealityK1DataUpdateCoordinator,
        websocket,
        name: str,
        icon: str | None = None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._websocket = websocket
        self._attr_name = name
        self._attr_icon = icon
        self._state = False  # Default state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: dict[str, Any]):
        """Turn the switch on."""
        await self._send_websocket_command(True)
        #self._state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: dict[str, Any]):
        """Turn the switch off."""
        await self._send_websocket_command(False)
        #self._state = False
        self.async_write_ha_state()

    #@property
    #def is_on(self) -> bool:
    #    """Return if the switch is on."""
    #    return self._state

    async def _send_websocket_command(self, is_on: bool) -> None:
        """Send the appropriate command to the printer via WebSocket."""
        raise NotImplementedError  # To be implemented in subclasses


class K1LightSwitch(K1Switch):
    """Representation of a Creality K1 light switch."""

    def __init__(
        self, coordinator: CrealityK1DataUpdateCoordinator, websocket
    ) -> None:
        """Initialize the light switch."""
        super().__init__(coordinator, websocket, "K1 Printer Light", "mdi:desk-lamp")
        self._attr_unique_id = "creality_k1_light"
        # Initial state from data
        if coordinator.data:
            light_sw_value = coordinator.data.get("lightSw")
            _LOGGER.debug(f"Switch: Initial lightSw value: {light_sw_value}")  # Add this line
    #        self._state = coordinator.data.get("lightSw") == 1

    async def _send_websocket_command(self, is_on: bool) -> None:
        """Send the command to turn the light on or off."""
        command = {"method": "set", "params": {"lightSw": 1 if is_on else 0}}
        _LOGGER.debug(f"Sending light command: {command}")  # Log the command
        await self._websocket.send_message(command)

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        # Om koordinatorn inte har data än, returnera None (okänt)
        if not self.coordinator.data:
            return None
        # Läs direkt från koordinatorns senaste data
        return self.coordinator.data.get("lightSw") == 1