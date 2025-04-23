"""Creality K1 Max Integration."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
#from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .websocket import MyWebSocket  # Din WebSocket-klass
from .coordinator import CrealityK1DataUpdateCoordinator  # Din DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

#PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.FAN]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Creality K1 Max from a config entry."""
    # 1. Hämta konfigurationsdata från config entry
    printer_ip = entry.data.get("ip_address")  # Hämta IP från config entry
    ws_url = f"ws://{printer_ip}:9999"

    # 2. Skapa en WebSocket-klient
    try:
        websocket = MyWebSocket(ws_url)
        _LOGGER.debug("async_setup_entry: Initializing WebSocket")
        await websocket.init(hass)
        _LOGGER.debug("async_setup_entry: WebSocket initialized")
    except Exception as e:
        _LOGGER.error(f"Could not connect to Creality K1 Max: {e}")
        raise ConfigEntryNotReady from e

    # 3. Skapa en DataUpdateCoordinator
    async def async_update_data():
        """Fetch data from Creality K1 Max."""
        try:
            data = await websocket.get_latest_data()
            _LOGGER.debug(f"async_update_data: Fetched data: {data}")
            return data
        except Exception as e:
            raise UpdateFailed(f"Error fetching data: {e}") from e

    coordinator = CrealityK1DataUpdateCoordinator(
    hass,
    websocket,  # Skicka websocket-instansen
    update_interval=timedelta(seconds=5),
    )

    # Fetch initial data so we have data when entities subscribe
    try:
        _LOGGER.debug("async_setup_entry: Performing first refresh")
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.debug("async_setup_entry: First refresh completed")
    except ConfigEntryNotReady:
        _LOGGER.debug("async_setup_entry: First refresh failed, trying refresh")
        await coordinator.async_refresh()
        _LOGGER.debug("async_setup_entry: Regular refresh completed")

    # Lagra coordinator och websocket i hass.data för åtkomst av plattformar
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    hass.data[DOMAIN]["websocket"] = websocket
    hass.data[DOMAIN]["latest_data"] = {}  # För att lagra den senaste datan

    # 4. Ställ in plattformarna (sensor,switch och fans)
    _LOGGER.debug("async_setup_entry: Setting up platforms")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("async_setup_entry: Platforms setup complete")

    # 5. Hantera unload
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    unload_ok = unload_ok and await hass.config_entries.async_forward_entry_unload(entry, "switch")

    websocket = hass.data[DOMAIN]["websocket"]
    await websocket.clear()

    if unload_ok:
        del hass.data[DOMAIN][entry.entry_id]

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload config entry."""
    return await hass.config_entries.async_reload(entry.entry_id)

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Running migration of config entry")
    return True