"""Creality K1 Max Integration."""
import asyncio
import logging
import homeassistant.helpers.device_registry as dr 

from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .websocket import MyWebSocket  # WebSocket class from websocket.py
from .coordinator import CrealityK1DataUpdateCoordinator  # DataUpdateCoordinator class from coordinator.py

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Creality K1 from a config entry."""
    # 1. Get configuration data from the config entry
    printer_ip = entry.data.get("ip_address")
    ws_url = f"ws://{printer_ip}:9999"

    # 2. Create and connect the WebSocket client
    # This will now raise ConnectionError on failure, which is caught below.
    websocket = MyWebSocket(ws_url)
    try:
        _LOGGER.debug("Initializing WebSocket and attempting to connect...")
        await websocket.init(hass)
        _LOGGER.debug("WebSocket initialized and connected successfully.")
    except ConnectionError as e:
        # If the initial connection fails, raise ConfigEntryNotReady.
        # Home Assistant will automatically retry the setup later.
        _LOGGER.warning(f"Could not connect to Creality K1 at {printer_ip}: {e}. Setup will be retried.")
        raise ConfigEntryNotReady from e

    # 3. Create the DataUpdateCoordinator
    coordinator = CrealityK1DataUpdateCoordinator(
        hass,
        websocket,  # Pass the connected websocket instance
        update_interval=timedelta(seconds=5),
    )

    # 4. Fetch initial data from the coordinator.
    # If this fails, ConfigEntryNotReady will be raised, and the setup will be retried.
    # We no longer catch it here, letting the failure stop the setup process.
    await coordinator.async_config_entry_first_refresh()

    # 5. If we get here, connection and first data fetch were successful.
    # Now, register the device with the correct name from the hostname.
    device_registry = dr.async_get(hass)
    if coordinator.data and (hostname := coordinator.data.get("hostname")):
        printer_model = coordinator.data.get("model", "K1 Series")
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            name=hostname,  # Use the fetched hostname as the device name
            manufacturer="Creality",
            model=printer_model,
        )
    else:
        # Fallback in case hostname is not available after a successful refresh
        _LOGGER.warning("Could not get hostname from initial data. Using default device name.")
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,  # Fallback to the title set during config flow
            manufacturer="Creality",
        )

    # 6. Store coordinator and websocket instances per entry for platform access
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "websocket": websocket,
    }

    # 7. Set up platforms (sensor, switch, fan)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 8. Set up an unload listener for when the entry is removed or reloaded
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload plattforms first
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, PLATFORMS) # Use PLATFORMS

    if unload_ok:
        # Get the specific websocket instance and close it.
        if entry.entry_id in hass.data[DOMAIN]:
            entry_data = hass.data[DOMAIN][entry.entry_id]
            if "websocket" in entry_data:
                websocket = entry_data["websocket"]
                await websocket.clear()

            # Delete all data for this entry
            hass.data[DOMAIN].pop(entry.entry_id)

        # Remove whole domain if no more entries 
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload config entry."""
    return await hass.config_entries.async_reload(entry.entry_id)

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Running migration of config entry")
    return True