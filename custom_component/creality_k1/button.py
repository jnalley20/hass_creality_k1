# Creality K1 Button Module
#
# Copyright (C) 2025 Joshua Wherrett <thejoshw.code@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, BUTTON_CONTROLS, DEVICE_MANUFACTURER, DEVICE_MODEL
from .coordinator import CrealityK1DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    ) -> None:
    """Set up the Creality K1 buttons from a config entry."""
    coordinator: CrealityK1DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id] # Get correct coordinator when having multiple printers
    buttons = []
    for (name, params) in BUTTON_CONTROLS:
        buttons.append(
            K1Button(
                coordinator,
                config_entry,
                name,
                params,
                name.lower().replace(' ','_')
            )
        )
    async_add_entities(buttons)

class K1Button(CoordinatorEntity, ButtonEntity):
    """Base class for Creality K1 buttons."""
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CrealityK1DataUpdateCoordinator,
        config_entry: ConfigEntry,
        name: str,
        params: dict,
        unique_id_suffix: str | None = None
        ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_name = name
        self._params = params
        self._attr_unique_id = f"{config_entry.entry_id}_button"
        if unique_id_suffix:
            self._attr_unique_id += f"_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
            via_device=(DOMAIN, config_entry.entry_id),
        )

    @property
    def available(self) -> bool:
        return self.coordinator.websocket.is_connected and super().available

    async def async_press(self):
        """Press the button."""
        await self._send_websocket_command()
        self.async_write_ha_state()

    async def _send_websocket_command(self) -> None:
        """Send the appropriate command to the printer via WebSocket."""
        command = {"method": "set", "params": self._params}
        _LOGGER.debug(f"Sending button command: {command}")  # Log the command
        await self.coordinator.websocket.send_message(command)