"""Constants for the Creality K1 integration."""

from homeassistant.const import Platform

DOMAIN = "creality_k1"  # Domänen för din integration
PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.FAN] # De plattformar som används

# WebSocket-relaterade konstanter
MSG_TYPE_MSG = "message"  # Vanligt meddelande
MSG_TYPE_HEARTBEAT = "heart_beat"  # Hjärtslagsmeddelande
HEARTBEAT_INTERVAL = 5  # Sekunder
HEARTBEAT_TIMEOUT = 1  # Sekunder
RECONNECT_INTERVAL = 5  # Sekunder

# Sensor-relaterade konstanter
SENSOR_NAME_BED_TEMP = "K1 Bed Temperature"
SENSOR_NAME_BOX_TEMP = "K1 Box Temperature"
SENSOR_NAME_NOZZLE_TEMP = "K1 Nozzle Temperature"
SENSOR_NAME_PRINT_PROGRESS = "K1 Print Progress"
SENSOR_NAME_TOTAL_LAYER = "K1 Total Layer Count"
SENSOR_NAME_WORKING_LAYER = "K1 Working Layer"
SENSOR_NAME_USED_MATERIAL = "K1 Used Material Length"
SENSOR_NAME_TOTAL_PRINT_TIME = "K1 Total Print Time"
SENSOR_NAME_PRINT_JOB_LEFT  = "K1 Print Job Left"

SWITCH_NAME_LIGHT = "K1 Printer Light"

FAN_NAME_MODEL_FAN = "Model Fan"
FAN_NAME_CASE_FAN = "Case Fan"
FAN_NAME_AUXILIARY_FAN = "Side Fan"
FAN_CONFIG = {
    FAN_NAME_MODEL_FAN: ("modelFanPct", "fan", 0),  # P0 for Case Fan
    FAN_NAME_CASE_FAN: ("caseFanPct", "fanCase", 1), # P1 for Case Fan
    FAN_NAME_AUXILIARY_FAN: ("auxiliaryFanPct", "fanAuxiliary", 2), # P2 for Aux Fan
}

# Enhetsinformation
DEVICE_NAME = "K1 Printer"
DEVICE_MANUFACTURER = "Creality"
DEVICE_MODEL = "K1 Max"
PRINTER_STATE_MAP = {
    0: "Stopped",        # Från "Printing stopped"
    1: "Printing",
    2: "Complete",       # Från "printing complete"
    3: "Failed",         # Från "Printing failed"
    4: "Aborted",        # Från "print abort"
    5: "Paused"          # Från "Printing Paused"
}
DEFAULT_PRINTER_STATE = "Unknown" # Ett standardvärde om koden inte finns