"""Creality K1 Max Integration."""
import asyncio
import logging
import homeassistant.helpers.device_registry as dr # Lägg till denna import högst upp

from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS, HASS_UPDATE_INTERVAL, DEVICE_MANUFACTURER
from .websocket import MyWebSocket  # Din WebSocket-klass
from .coordinator import CrealityK1DataUpdateCoordinator  # Din DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Creality K1 Max from a config entry."""

    # Lagra coordinator/websocket per entry (som tidigare fixat)
    hass.data.setdefault(DOMAIN, {})
    coordinator = CrealityK1DataUpdateCoordinator(hass, config_entry)
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    # --- Initial Device Registration (Minimal) ---
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.entry_id)},
        name=config_entry.title, # Använd entry title temporärt
        manufacturer=DEVICE_MANUFACTURER,
    )
    # --- End Initial Registration ---

    hostname_set_flag = False # Flagga för att bara uppdatera en gång

    # Listener-funktion
    def _update_device_name_listener():
        nonlocal hostname_set_flag
        if hostname_set_flag or not coordinator.data:
            return # Redan uppdaterad eller ingen data
        hostname = coordinator.data.get("hostname")
        printer_model = coordinator.data.get("model", "K1 Series")
        if hostname:
            _LOGGER.info(f"Hostname '{hostname}' found, updating device name.")
            # Uppdatera enhetsposten med korrekt namn och modell
            device_registry.async_get_or_create( # Används för att uppdatera
                config_entry_id=config_entry.entry_id,
                identifiers={(DOMAIN, config_entry.entry_id)},
                name=hostname, # SÄTT RÄTT NAMN
                manufacturer=DEVICE_MANUFACTURER,
                model=printer_model,
            )
            hostname_set_flag = True # Markera som uppdaterad
            # remove_listener() # Ta eventuellt bort listenern efter lyckad uppdatering

    # Försök första refresh
    try:
        await coordinator.async_config_entry_first_refresh()
        # Försök uppdatera namnet direkt om data finns
        _update_device_name_listener()
    except ConfigEntryNotReady:
        _LOGGER.warning("First refresh failed, device name will be updated later by listener.")
        # Fortsätt setup ändå

    # Lägg till listener som körs efter framtida lyckade coordinator-uppdateringar
    remove_listener = coordinator.async_add_listener(_update_device_name_listener)
    # Se till att listener tas bort när entry avlastas
    config_entry.async_on_unload(remove_listener)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms first
    #unload_ok = await hass.config_entries.async_forward_entry_unload(config_entry, PLATFORMS) # Use PLATFORMS
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS) # Use PLATFORMS

    if unload_ok:
        # Get the specific websocket instance and close it.
        if config_entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][config_entry.entry_id]
            await coordinator.websocket.disconnect()

            # Delete all data for this entry
            hass.data[DOMAIN].pop(config_entry.entry_id)

        # Remove whole domain if no more entries 
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Reload config entry."""
    return await hass.config_entries.async_reload(config_entry.entry_id)

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Running migration of config entry")
    return True