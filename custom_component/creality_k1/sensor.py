"""Platform for Creality K1 sensor."""
import logging
from typing import Any

from homeassistant.const import UnitOfTemperature, PERCENTAGE, UnitOfTime
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PRINTER_STATE_MAP, DEFAULT_PRINTER_STATE
from .coordinator import CrealityK1DataUpdateCoordinator  # Din DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Creality K1 sensors."""
    coordinator: CrealityK1DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([
        K1NozzleTemperatureSensor(coordinator),
        K1BedTemperatureSensor(coordinator),
        K1BoxTemperatureSensor(coordinator),
        K1PrintProgressSensor(coordinator),
        K1TotalLayerSensor(coordinator),
        K1WorkingLayerSensor(coordinator),
        K1UsedMaterialSensor(coordinator),
        K1PrintJobTimeSensor(coordinator),
        K1PrintLeftTimeSensor(coordinator),
        K1PrintState(coordinator),
    ])


class K1Sensor(CoordinatorEntity, SensorEntity):
    """Base class for Creality K1 sensors."""

    def __init__(
        self,
        coordinator: CrealityK1DataUpdateCoordinator,
        name: str,
        device_class: SensorDeviceClass | None = None,
        unit_of_measurement: str | None = None,
        state_class: SensorStateClass | None = None,
        icon: str | None = None,
        unique_id: str | None = None,  # Lägg till unique_id här
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_state_class = state_class
        self._attr_icon = icon
        self._attr_unique_id = unique_id  # Lägg till unique_id här

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class K1NozzleTemperatureSensor(K1Sensor):
    """Representation of a Creality K1 Nozzle Temperature sensor."""

    def __init__(
        self, coordinator: CrealityK1DataUpdateCoordinator
    ) -> None:
        """Initialize the nozzle temperature sensor."""
        super().__init__(
            coordinator,
            name="K1 Nozzle Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            unit_of_measurement=UnitOfTemperature.CELSIUS,
            unique_id="creality_k1_nozzle_temperature",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current nozzle temperature."""
        if self.coordinator.data:
            nozzle_temp = self.coordinator.data.get("nozzleTemp")
            if isinstance(nozzle_temp, str):
                try:
                    return float(nozzle_temp)
                except ValueError:
                    _LOGGER.warning(f"Invalid nozzleTemp value: {nozzle_temp}")
                    return None
            elif isinstance(nozzle_temp, (int, float)):
                return float(nozzle_temp)
        return None

    @property
    def extra_state_attributes(self):
        """Return the sensor attributes."""
        if self.coordinator.data:
            return {
                "target": self.coordinator.data.get("targetNozzleTemp"),
                "max": self.coordinator.data.get("maxNozzleTemp"),
            }
        return {}


class K1BedTemperatureSensor(K1Sensor):
    """Representation of a Creality K1 Bed Temperature sensor."""

    def __init__(
        self, coordinator: CrealityK1DataUpdateCoordinator
    ) -> None:
        """Initialize the bed temperature sensor."""
        super().__init__(
            coordinator,
            name="K1 Bed Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            unit_of_measurement=UnitOfTemperature.CELSIUS,
            unique_id="creality_k1_bed_temperature",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current bed temperature."""
        if self.coordinator.data:
            bed_temp = self.coordinator.data.get("bedTemp0")
            if isinstance(bed_temp, str):
                try:
                    return float(bed_temp)
                except ValueError:
                    _LOGGER.warning(f"Invalid bedTemp0 value: {bed_temp}")
                    return None
            elif isinstance(bed_temp, (int, float)):
                return float(bed_temp)
        return None

    @property
    def extra_state_attributes(self):
        """Return the sensor attributes."""
        if self.coordinator.data:
            return {
                "target": self.coordinator.data.get("targetBedTemp0"),
                "max": self.coordinator.data.get("maxBedTemp"),
            }
        return {}


class K1BoxTemperatureSensor(K1Sensor):
    """Representation of a Creality K1 Box Temperature sensor."""

    def __init__(
        self, coordinator: CrealityK1DataUpdateCoordinator
    ) -> None:
        """Initialize the box temperature sensor."""
        super().__init__(
            coordinator,
            name="K1 Box Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            unit_of_measurement=UnitOfTemperature.CELSIUS,
            unique_id="creality_k1_box_temperature",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current box temperature."""
        if self.coordinator.data:
            box_temp = self.coordinator.data.get("boxTemp")
            if isinstance(box_temp, str):
                try:
                    return float(box_temp)
                except ValueError:
                    _LOGGER.warning(f"Invalid boxTemp value: {box_temp}")
                    return None
            elif isinstance(box_temp, (int, float)):
                return float(box_temp)
        return None


class K1PrintProgressSensor(K1Sensor):
    """Representation of a Creality K1 Print Progress sensor."""

    def __init__(
        self, coordinator: CrealityK1DataUpdateCoordinator
    ) -> None:
        """Initialize the print progress sensor."""
        super().__init__(
            coordinator,
            name="K1 Print Progress",
            unique_id="creality_k1_print_progress",
            unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT
        )
        self._attr_icon = "mdi:percent"

    @property
    def native_value(self) -> int | None:
        """Return the current print progress."""
        if self.coordinator.data:
            progress = self.coordinator.data.get("printProgress")
            if isinstance(progress, str):
                try:
                    return int(progress)
                except ValueError:
                    _LOGGER.warning(f"Invalid printProgress value: {progress}")
                    return None
            elif isinstance(progress, int):
                return progress
        return None


class K1TotalLayerSensor(K1Sensor):
    """Representation of a Creality K1 Total Layer sensor."""

    def __init__(
        self, coordinator: CrealityK1DataUpdateCoordinator
    ) -> None:
        """Initialize the total layer sensor."""
        super().__init__(
            coordinator,
            name="K1 Total Layer Count",
            unique_id="creality_k1_total_layer_count",
        )
        self._attr_icon = "mdi:layers"

    @property
    def native_value(self) -> int | None:
        """Return the total layer count."""
        if self.coordinator.data:
            total_layer = self.coordinator.data.get("TotalLayer")
            if isinstance(total_layer, str):
                try:
                    return int(total_layer)
                except ValueError:
                    _LOGGER.warning(f"Invalid TotalLayer value: {total_layer}")
                    return None
            elif isinstance(total_layer, int):
                return total_layer
        return None


class K1WorkingLayerSensor(K1Sensor):
    """Representation of a Creality K1 Working Layer sensor."""

    def __init__(
        self, coordinator: CrealityK1DataUpdateCoordinator
    ) -> None:
        """Initialize the working layer sensor."""
        super().__init__(
            coordinator,
            name="K1 Working Layer",
            unique_id="creality_k1_working_layer",
        )
        self._attr_icon = "mdi:cube-outline"

    @property
    def native_value(self) -> int | None:
        """Return the current working layer."""
        if self.coordinator.data:
            layer = self.coordinator.data.get("layer")
            if isinstance(layer, str):
                try:
                    return int(layer)
                except ValueError:
                    _LOGGER.warning(f"Invalid layer value: {layer}")
                    return None
            elif isinstance(layer, int):
                return layer
        return None


class K1UsedMaterialSensor(K1Sensor):
    """Representation of a Creality K1 Used Material sensor."""

    def __init__(
        self, coordinator: CrealityK1DataUpdateCoordinator
    ) -> None:
        """Initialize the used material sensor."""
        super().__init__(
            coordinator,
            name="K1 Used Material Length",
            unit_of_measurement="cm",
            unique_id="creality_k1_used_material_length",
            state_class=SensorStateClass.MEASUREMENT
        )
        self._attr_icon = "mdi:tape"

    @property
    def native_value(self) -> int | None:
        """Return the used material length."""
        if self.coordinator.data:
            used_material = self.coordinator.data.get("usedMaterialLength")
            if isinstance(used_material, str):
                try:
                    return int(used_material)
                except ValueError:
                    _LOGGER.warning(f"Invalid usedMaterialLength value: {used_material}")
                    return None
            elif isinstance(used_material, int):
                return used_material
        return None
    
class K1PrintJobTimeSensor(K1Sensor):
    """K1 Print Job Time Sensor."""
    def __init__(
        self, coordinator: CrealityK1DataUpdateCoordinator
    ) -> None:
        """Initialize the print job time sensor."""
        super().__init__(
            coordinator, 
            name="Print Job Time",
            unit_of_measurement="s",
            unique_id="creality_k1_print_job_time",
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT
        )
        self._attr_icon = "mdi:timer-sand"

    @property
    def native_value(self) -> int | None:
        """Return the print job time."""
        if self.coordinator.data:
            print_job_time = self.coordinator.data.get("printJobTime")
            if isinstance(print_job_time, str):
                try:
                    return int(print_job_time)
                except ValueError:
                    _LOGGER.warning(f"Invalid printJobTime value: {print_job_time}")
                    return None
            elif isinstance(print_job_time, int):
                return print_job_time
        return None
    
class K1PrintLeftTimeSensor(K1Sensor):
    """K1 Print Job Left Sensor."""
    def __init__(
        self, coordinator: CrealityK1DataUpdateCoordinator
    ) -> None:
        """Initialize the print job left sensor."""
        super().__init__(
            coordinator, 
            name="Print Left Time",
            unit_of_measurement="s",
            unique_id="creality_k1_print_left_time",
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT
        )
        self._attr_icon = "mdi:timer-sand"

    @property
    def native_value(self) -> int | None:
        """Return the print left time."""
        if self.coordinator.data:
            print_left_time = self.coordinator.data.get("printLeftTime")
            if isinstance(print_left_time, str):
                try:
                    return int(print_left_time)
                except ValueError:
                    _LOGGER.warning(f"Invalid printLeftTime value: {print_left_time}")
                    return None
            elif isinstance(print_left_time, int):
                return print_left_time
        return None
    
class K1PrintState(K1Sensor): 
    """K1 Print State Sensor"""
    def __init__(
        self, coordinator: CrealityK1DataUpdateCoordinator
    ) -> None:
        """Initialize the print state Sensor."""
        super().__init__(
            coordinator,
            name="Print State",
            unique_id="creality_k1_print_state_sensor",
        )
        self._attr_icon = "mdi:printer-3d"


    @property
    def native_value(self) -> str | None: # Ändra returtyp till str | None
        """Return The Printers State as a descriptive string."""
        raw_state_value = None
        if self.coordinator.data:
            raw_state_value = self.coordinator.data.get("state")

        # Försök konvertera till int om det är en sträng eller redan int
        int_state: int | None = None
        if isinstance(raw_state_value, (int, str)):
            try:
                int_state = int(raw_state_value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid non-integer state value received: {raw_state_value}")
        elif raw_state_value is not None:
             _LOGGER.warning(f"Unexpected state value type: {type(raw_state_value)} ({raw_state_value})")


        # Om vi har ett giltigt heltal, slå upp i mappningen
        if int_state is not None:
            # .get() returnerar strängen om nyckeln finns, annars DEFAULT_PRINTER_STATE
            return PRINTER_STATE_MAP.get(int_state, DEFAULT_PRINTER_STATE)

        # Om ingen data eller ogiltigt state, returnera default
        return DEFAULT_PRINTER_STATE # Eller returnera None om du föredrar det för okänt state