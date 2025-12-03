"""
Seplos V2 / V16 BMS Data Fetcher
Reads one or more Seplos protocol v2.0 BMS (in parallel) via
(remote) serial connection(s) and publishes their data to MQTT
"""
import sys
import os
import signal
import logging
import time
from datetime import datetime
import json
from typing import Optional, Dict, Any, Union, List, Callable
import serial
from serial.serialutil import SerialException
import paho.mqtt.client as mqtt
from paho.mqtt import MQTTException
from ha_auto_discovery import AutoDiscoveryConfig

# Type aliases for clarity
ConfigValue = Union[int, float, bool, str, None]
BatteryData = Dict[str, Any]

# State container for shared application state
class AppState:
    """Container for globally shared runtime objects."""
    def __init__(self):
        self.mqtt_client: Optional[mqtt.Client] = None
        self.serial_instance: Optional[serial.Serial] = None
        self.battery_packs: List[Dict[str, Any]] = []

app_state = AppState()

logger: Optional[logging.Logger] = None


def graceful_exit(signum: Optional[int] = None, _frame: Optional[Any] = None) -> None:
    """Handle script exit to disconnect MQTT gracefully and cleanup."""

    try:
        # Close MQTT client if connected
        if app_state.mqtt_client and app_state.mqtt_client.is_connected():
            if logger:
                logger.info("Sending offline status to MQTT")
            app_state.mqtt_client.publish(f"{os.getenv('MQTT_TOPIC', 'seplos')}/availability", "offline", retain=True)
            if logger:
                logger.info("Disconnecting MQTT client")
            app_state.mqtt_client.disconnect()
            app_state.mqtt_client.loop_stop()

        # Close serial connections if open
        if app_state.serial_instance and app_state.serial_instance.isOpen():
            if logger:
                logger.info("Closing serial connection")
            app_state.serial_instance.close()
    except Exception as e:
        if logger:
            logger.error("Error during graceful exit: %s", e)

    if signum is not None:
        sys.exit(0)


# Register signal handler for SIGTERM
signal.signal(signal.SIGTERM, graceful_exit)
signal.signal(signal.SIGINT, graceful_exit)


def get_env_value(var_name: str, default: Any = None, return_type: type = str) -> ConfigValue:
    """
    Get configuration value from environment variable with type casting.

    Args:
        var_name: Environment variable name
        default: Default value if not set
        return_type: Target type for casting (int, float, bool, str)

    Returns:
        Casted value or default
    """
    value = os.getenv(var_name, default)

    if value is None or value == "":
        return default

    try:
        if return_type == int:
            return int(value)
        elif return_type == float:
            return float(value)
        elif return_type == bool:
            if isinstance(value, bool):
                return value
            return str(value).lower() in ['true', '1', 'yes', 'on']
        else:
            return str(value)
    except (ValueError, TypeError):
        return default


# Configuration from environment variables with defaults
class Config:
    """Configuration class holding all settings from environment variables."""

    # BMS Configuration
    MIN_CELL_VOLTAGE = get_env_value("MIN_CELL_VOLTAGE", 2.500, float)
    MAX_CELL_VOLTAGE = get_env_value("MAX_CELL_VOLTAGE", 3.650, float)
    NUMBER_OF_PACKS = get_env_value("NUMBER_OF_PACKS", 1, int)

    # Serial Configuration
    SERIAL_INTERFACE = get_env_value("SERIAL_INTERFACE", "/tmp/vcom0", str)

    # MQTT Configuration
    MQTT_HOST = get_env_value("MQTT_HOST", "192.168.1.100", str)
    MQTT_PORT = get_env_value("MQTT_PORT", 1883, int)
    MQTT_USERNAME = get_env_value("MQTT_USERNAME", "seplos-mqtt", str)
    MQTT_PASSWORD = get_env_value("MQTT_PASSWORD", "", str)
    MQTT_TOPIC = get_env_value("MQTT_TOPIC", "seplos", str)
    MQTT_UPDATE_INTERVAL = get_env_value("MQTT_UPDATE_INTERVAL", 0, int)

    # Home Assistant Discovery
    ENABLE_HA_DISCOVERY_CONFIG = get_env_value("ENABLE_HA_DISCOVERY_CONFIG", True, bool)
    HA_DISCOVERY_PREFIX = get_env_value("HA_DISCOVERY_PREFIX", "homeassistant", str)
    INVERT_HA_DIS_CHARGE_MEASUREMENTS = get_env_value("INVERT_HA_DIS_CHARGE_MEASUREMENTS", True, bool)

    # Logging
    LOGGING_LEVEL = get_env_value("LOGGING_LEVEL", "info", str).upper()


# Logging setup
logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("SeplosBMS")

# Set log level based on configuration
log_levels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR
}
logger.setLevel(log_levels.get(Config.LOGGING_LEVEL, logging.INFO))

# Log configuration on startup
logger.info("Starting Seplos BMS Data Fetcher")
logger.debug("Configuration loaded: %s", vars(Config))


class Telemetry:
    """Holds numeric states for different sensors."""

    def __init__(self):
        # From pack
        self.cell_voltage: List[Optional[float]] = [None] * 16
        self.cell_temperature: List[Optional[float]] = [None] * 4
        self.ambient_temperature: Optional[float] = None
        self.components_temperature: Optional[float] = None
        self.dis_charge_current: Optional[float] = None
        self.total_pack_voltage: Optional[float] = None
        self.residual_capacity: Optional[float] = None
        self.battery_capacity: Optional[float] = None
        self.state_of_charge: Optional[float] = None
        self.rated_capacity: Optional[float] = None
        self.charging_cycles: Optional[int] = None
        self.state_of_health: Optional[float] = None
        self.port_voltage: Optional[float] = None

        # From user settings
        self.min_cell_voltage: Optional[float] = None
        self.max_cell_voltage: Optional[float] = None

        # Calculated
        self.average_cell_voltage: Optional[float] = None
        self.delta_cell_voltage: Optional[float] = None
        self.lowest_cell: Optional[int] = None
        self.lowest_cell_voltage: Optional[float] = None
        self.highest_cell: Optional[int] = None
        self.highest_cell_voltage: Optional[float] = None
        self.min_pack_voltage: Optional[float] = None
        self.max_pack_voltage: Optional[float] = None
        self.delta_cell_temperature: Optional[float] = None
        self.dis_charge_power: Optional[float] = None


class Telesignalization:
    """Holds warning, protection, lockout, normal, on and off states for different alarms."""

    def __init__(self):
        # 24 byte alarms
        self.cell_voltage_alarm: List[Optional[str]] = [None] * 16
        self.cell_temperature_alarm: List[Optional[str]] = [None] * 4
        self.ambient_temperature_alarm: Optional[str] = None
        self.component_temperature_alarm: Optional[str] = None
        self.dis_charging_current_alarm: Optional[str] = None
        self.pack_voltage_alarm: Optional[str] = None

        # 20 bit alarms (grouped for clarity)
        self.alarms = {
            # Warning 1 - System failures
            'voltage_sensing_failure': None,
            'temperature_sensing_failure': None,
            'current_sensing_failure': None,
            'power_switch_failure': None,
            'cell_voltage_difference_sensing_failure': None,
            'charging_switch_failure': None,
            'discharging_switch_failure': None,
            'current_limit_switch_failure': None,

            # Warning 2 - Voltage issues
            'cell_overvoltage': None,
            'cell_voltage_low': None,
            'pack_overvoltage': None,
            'pack_voltage_low': None,

            # Warning 3 - Temperature issues
            'charging_temperature_high': None,
            'charging_temperature_low': None,
            'discharging_temperature_high': None,
            'discharging_temperature_low': None,

            # Warning 4 - Ambient temperature
            'ambient_temperature_high': None,
            'ambient_temperature_low': None,
            'component_temperature_high': None,
            'low_temperature_heating': None,

            # Warning 5 - Current issues
            'charging_overcurrent': None,
            'discharging_overcurrent': None,
            'transient_overcurrent': None,
            'output_short_circuit': None,

            # Warning 6 - Miscellaneous
            'charging_high_voltage_protection': None,
            'intermittent_power_supplement': None,
            'soc_low': None,
            'cell_low_voltage_forbidden_charging': None,
            'output_reverse_polarity_protection': None,
            'output_connection_failure': None,

            # Warning 7 - Charging wait
            'auto_charging_wait': None,
            'manual_charging_wait': None,

            # Warning 8 - System errors
            'eep_storage_failure': None,
            'rtc_clock_failure': None,
            'no_calibration_of_voltage': None,
            'no_calibration_of_current': None,
            'no_calibration_of_null_point': None
        }

        # Initialize warning attributes for backward compatibility
        for key in self.alarms:
            setattr(self, key, None)

        # Switch status
        self.discharge_switch: Optional[str] = None
        self.charge_switch: Optional[str] = None
        self.current_limit_switch: Optional[str] = None
        self.heating_switch: Optional[str] = None

        # Passive balancing status
        self.balancer_cell: List[Optional[str]] = [None] * 16

        # System status
        self.system_status: Optional[str] = None

        # Cell disconnection status
        self.disconnection_cell: List[Optional[str]] = [None] * 16


class SeplosBatteryPack:
    """Handles all methods for fetching, validating and parsing BMS data."""

    FRAME_READ_RETRIES = 5
    FRAME_MIN_LENGTH = 81
    STATUS_MAP_24_BYTE_ALARM = {
        0: "OK",
        1: "Alarm (low)",
        2: "Alarm (high)"
    }
    STATUS_MAP_20_BIT_ALARM = {
        "on_off": ("ON", "OFF"),
        "fault_normal": ("Fault", "OK"),
        "warning_normal": ("Warning", "OK"),
        "protection_normal": ("Protection", "OK"),
    }

    def __init__(self, pack_address: int):
        self.pack_address = pack_address
        self.last_status: Optional[BatteryData] = None
        self.telemetry = Telemetry()
        self.telesignalization = Telesignalization()

    @staticmethod
    def calculate_frame_checksum(frame: bytes) -> int:
        """Calculate frame checksum."""
        checksum = sum(frame) % 0xFFFF
        checksum ^= 0xFFFF
        checksum += 1
        return checksum

    @staticmethod
    def is_valid_hex_string(data: bytes) -> bool:
        """Check if given ASCII data is valid hex."""
        try:
            bytes.fromhex(data.decode("ascii"))
            logger.debug("Frame has hex only: OK")
            return True
        except (ValueError, UnicodeDecodeError):
            logger.debug("Frame includes non-hexadecimal characters: %s", data)
            return False

    @staticmethod
    def is_valid_length(data: bytes, expected_length: int) -> bool:
        """Check if given data matches expected length."""
        actual_length = len(data)
        if actual_length != expected_length:
            logger.debug(
                "Frame length mismatch - expected: %s, got: %s",
                expected_length,
                actual_length
            )
            return False
        logger.debug("Frame length OK: %s", expected_length)
        return True

    @staticmethod
    def int_from_1byte_hex_ascii(data: bytes, offset: int, signed: bool = False) -> int:
        """Return (signed) int value from 1 byte ASCII hex data."""
        return int.from_bytes(
            bytes.fromhex(data[offset:offset + 2].decode("ascii")),
            byteorder="big",
            signed=signed
        )

    @staticmethod
    def int_from_2byte_hex_ascii(data: bytes, offset: int, signed: bool = False) -> int:
        """Return (signed) int value from 2 byte ASCII hex data."""
        return int.from_bytes(
            bytes.fromhex(data[offset:offset + 4].decode("ascii")),
            byteorder="big",
            signed=signed
        )

    @staticmethod
    def status_from_24_byte_alarm(data: bytes, offset: int) -> str:
        """Return status string from 24 byte alarm data."""
        alarm_type = bytes.fromhex(data.decode("ascii"))[offset]
        return SeplosBatteryPack.STATUS_MAP_24_BYTE_ALARM.get(alarm_type, "Alarm (other)")

    @staticmethod
    def status_from_20_bit_alarm(
        data: bytes,
        offset: int,
        mode: str,
        first_bit: int,
        second_bit: Optional[int] = None
    ) -> str:
        """Return a status string based on 20-bit alarm data."""

        # Decode hex data into a byte value
        data_byte = bytes.fromhex(data.decode("ascii"))[offset]

        # helper
        def bit_set(bit: int) -> bool:
            return bool(data_byte & (1 << bit))

        # one bit mode
        if mode in SeplosBatteryPack.STATUS_MAP_20_BIT_ALARM:
            active, inactive = SeplosBatteryPack.STATUS_MAP_20_BIT_ALARM[mode]
            return active if bit_set(first_bit) else inactive

        # two bit mode
        if mode == "protection_alarm_normal":
            if bit_set(first_bit):
                return "Alarm"
            if second_bit is not None and bit_set(second_bit):
                return "Protection"
            return "OK"

        if mode == "lockout_protection_normal":
            if bit_set(first_bit):
                return "Protection"
            if second_bit is not None and bit_set(second_bit):
                return "Lockout"
            return "OK"

        return "unknown"

    def is_valid_frame(self, data: bytes) -> bool:
        """
        Check validity of frame: length, checksum and error flag.
        - Checksum must be valid
        - cid2 must be 00 (no error)
        """
        try:
            # Check frame checksum
            chksum = self.calculate_frame_checksum(data[1:-5])
            expected = self.int_from_2byte_hex_ascii(data, -5)
            if chksum != expected:
                logger.debug(
                    "Frame checksum mismatch - got: %s, expected: %s",
                    chksum,
                    expected
                )
                return False
            logger.debug("Frame checksum OK: %s", chksum)

            # Check frame cid2 flag
            cid2 = data[7:9]
            if cid2 != b"00":
                logger.debug(
                    "Frame error flag (cid2) set - expected b'00', got: %s",
                    cid2
                )
                return False
            logger.debug("Frame error flag OK: %s", cid2)

            return True

        except (UnicodeDecodeError, ValueError) as e:
            logger.debug("Frame validation error: %s", e)
            return False

    @staticmethod
    def get_info_length(info: bytes) -> int:
        """Calculate info length with checksum."""
        lenid = len(info)
        if lenid == 0:
            return 0

        lchksum = (lenid & 0xF) + ((lenid >> 4) & 0xF) + ((lenid >> 8) & 0xF)
        lchksum %= 16
        lchksum ^= 0xF
        lchksum += 1

        return (lchksum << 12) + lenid

    def encode_cmd(self, address: int, cid2: int, info: bytes = b"01") -> bytes:
        """Encode command for battery pack using its address."""
        cid1 = 0x46
        info_length = self.get_info_length(info)
        frame = f"{0x20:02X}{address:02X}{cid1:02X}{cid2:02X}{info_length:04X}".encode()
        frame += info
        checksum = self.calculate_frame_checksum(frame)
        return b"~" + frame + f"{checksum:04X}".encode() + b"\r"

    def get_lowest_cell(self) -> Dict[str, Any]:
        """Get lowest cell number and voltage."""
        valid_cells = [v for v in self.telemetry.cell_voltage if v is not None]
        if not valid_cells:
            return {"lowest_cell": 0, "lowest_cell_voltage": 0}

        lowest_voltage = min(valid_cells)
        lowest_cell = self.telemetry.cell_voltage.index(lowest_voltage)
        return {"lowest_cell": lowest_cell, "lowest_cell_voltage": lowest_voltage}

    def get_highest_cell(self) -> Dict[str, Any]:
        """Get highest cell number and voltage."""
        valid_cells = [v for v in self.telemetry.cell_voltage if v is not None]
        if not valid_cells:
            return {"highest_cell": 0, "highest_cell_voltage": 0}

        highest_voltage = max(valid_cells)
        highest_cell = self.telemetry.cell_voltage.index(highest_voltage)
        return {"highest_cell": highest_cell, "highest_cell_voltage": highest_voltage}

    def decode_telemetry_feedback_frame(self, data: bytes) -> Dict[str, Any]:
        """Decode battery pack telemetry feedback frame."""
        telemetry_feedback = {"normal": {}}
        feedback = telemetry_feedback["normal"]

        # Number of cells
        number_of_cells = self.int_from_1byte_hex_ascii(data, offset=4)

        # Static values from configs

        ## calculate min/max cell and pack voltages
        self.telemetry.min_cell_voltage = Config.MIN_CELL_VOLTAGE
        self.telemetry.max_cell_voltage = Config.MAX_CELL_VOLTAGE
        self.telemetry.min_pack_voltage = Config.MIN_CELL_VOLTAGE * number_of_cells
        self.telemetry.max_pack_voltage = Config.MAX_CELL_VOLTAGE * number_of_cells

        ### Add to telemetry_feedback
        feedback.update({
            "min_cell_voltage": self.telemetry.min_cell_voltage,
            "max_cell_voltage": self.telemetry.max_cell_voltage,
            "min_pack_voltage": self.telemetry.min_pack_voltage,
            "max_pack_voltage": self.telemetry.max_pack_voltage
        })

        # Dynamic values from the BMS

        telemetry_fields = {
            'cell_voltage':             { 'offset': 6,   'scale': 1/1000, 'round': 3, 'amount': number_of_cells },
            'cell_temperature':         { 'offset': 72,  'scale': 1/10, 'round': 1,  'bias': -2731, 'amount': 4 },
            'ambient_temperature':      { 'offset': 88,  'scale': 1/10, 'round': 1,  'bias': -2731 },
            'components_temperature':   { 'offset': 92,  'scale': 1/10, 'round': 1,  'bias': -2731 },
            'dis_charge_current':       { 'offset': 96,  'scale': 1/100, 'round': 2, 'signed': True },
            'total_pack_voltage':       { 'offset': 100, 'scale': 1/100, 'round': 2 },
            'residual_capacity':        { 'offset': 104, 'scale': 1/100, 'round': 2 },
            'battery_capacity':         { 'offset': 110, 'scale': 1/100, 'round': 1 },
            'state_of_charge':          { 'offset': 114, 'scale': 1/10, 'round': 1 },
            'rated_capacity':           { 'offset': 118, 'scale': 1/100, 'round': 1 },
            'charging_cycles':          { 'offset': 122 },
            'state_of_health':          { 'offset': 126, 'scale': 1/10, 'round': 1 },
            'port_voltage':             { 'offset': 130, 'scale': 1/100, 'round': 2 }
        }

        ## Fetch values for all telemetry fields
        for attr, cfg in telemetry_fields.items():
            offset = cfg["offset"]
            scale = cfg.get("scale", 1)
            rounding = cfg.get("round", None)
            bias = cfg.get("bias", 0)
            signed = cfg.get("signed", False)
            amount = cfg.get("amount", 1)

            if amount > 1:
                for i in range(amount):
                    raw = self.int_from_2byte_hex_ascii(
                        data,
                        offset + i * 4,
                        signed=signed
                    )
                    value = (raw + bias) * scale
                    if rounding is not None:
                        value = round(value, rounding)
                    getattr(self.telemetry, attr)[i] = value

                    ### Add to telemetry_feedback
                    feedback[f"{attr}_{i + 1}"] = value
            else:
                raw = self.int_from_2byte_hex_ascii(
                    data,
                    offset,
                    signed=signed
                )
                value = (raw + bias) * scale
                if rounding is not None:
                    value = round(value, rounding)
                setattr(self.telemetry, attr, value)

                ### Add to telemetry_feedback
                feedback[attr] = value

        # Calculated values

        # Get values from previous readings
        dis_charge_current  = self.telemetry.dis_charge_current
        total_pack_voltage  = self.telemetry.total_pack_voltage
        cell_voltages       = self.telemetry.cell_voltage
        cell_temps          = self.telemetry.cell_temperature

        ## Dis-/charge power
        dis_charge_power = round(dis_charge_current * total_pack_voltage, 2)
        self.telemetry.dis_charge_power = dis_charge_power

        ## Average cell voltage
        avg_voltage = round(sum(cell_voltages) / len(cell_voltages), 3)
        self.telemetry.average_cell_voltage = avg_voltage

        ## Highest/lowest cell and voltage
        lowest_idx, lowest_voltage = min(
            enumerate(cell_voltages), key=lambda x: x[1]
        )
        highest_idx, highest_voltage = max(
            enumerate(cell_voltages), key=lambda x: x[1]
        )
        self.telemetry.lowest_cell = lowest_idx
        self.telemetry.lowest_cell_voltage = lowest_voltage
        self.telemetry.highest_cell = highest_idx
        self.telemetry.highest_cell_voltage = highest_voltage

        ## Delta cell voltage
        delta_cell_voltage = round(highest_voltage - lowest_voltage, 3)
        self.telemetry.delta_cell_voltage = delta_cell_voltage

        # Delta cell temperature
        delta_cell_temperature = round(
            max(cell_temps) - min(cell_temps), 1
        )
        self.telemetry.delta_cell_temperature = delta_cell_temperature

        ### Add to telemetry_feedback
        feedback.update({
            "dis_charge_power": dis_charge_power,
            "average_cell_voltage": avg_voltage,
            "lowest_cell": lowest_idx + 1,      # 1-based for display
            "lowest_cell_voltage": lowest_voltage,
            "highest_cell": highest_idx + 1,    # 1-based for display
            "highest_cell_voltage": highest_voltage,
            "delta_cell_voltage": delta_cell_voltage,
            "delta_cell_temperature": delta_cell_temperature,
            "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        return telemetry_feedback

    def decode_telesignalization_feedback_frame(self, data: bytes) -> Dict[str, Any]:
        """Decode battery pack telesignalization feedback frame."""
        telesignalization_feedback = {"normal": {}, "binary": {}}
        feedback_normal = telesignalization_feedback["normal"]
        feedback_binary = telesignalization_feedback["binary"]

        # Number of cells
        number_of_cells = bytes.fromhex(data.decode("ascii"))[2]

        # 24-Byte alarms

        byte_alarm_fields = {
            'cell_voltage_alarm':           { 'offset': 3,   'amount': number_of_cells },
            'cell_temperature_alarm':       { 'offset': 20,  'amount': 4 },
            'ambient_temperature_alarm':    { 'offset': 24 },
            'component_temperature_alarm':  { 'offset': 25 },
            'dis_charging_current_alarm':   { 'offset': 26 },
            'pack_voltage_alarm':           { 'offset': 27 }
        }

        ## Fetch values for all byte_alarm fields
        for attr, cfg in byte_alarm_fields.items():
            offset = cfg["offset"]
            amount = cfg.get("amount", 1)

            if amount > 1:
                for i in range(amount):
                    value = self.status_from_24_byte_alarm(
                        data,
                        offset + i
                    )
                    getattr(self.telesignalization, attr)[i] = value

                    ### Add to telesignalization_feedback
                    feedback_normal[f"{attr}_{i + 1}"] = value
            else:
                value = self.status_from_24_byte_alarm(
                    data,
                    offset
                )
                setattr(self.telesignalization, attr, value)

                ### Add to telesignalization_feedback
                feedback_normal[attr] = value

        # Calculated values

        ## General cell voltage alarm if any of the cells has an active alarm
        feedback_normal["any_cell_voltage_alarm"] = (
            "Alarm" if any(cva != "OK" for cva in self.telesignalization.cell_voltage_alarm) else "OK"
        )

        ## General cell temperature alarm if any of the cells has an active alarm
        feedback_normal["any_cell_temperature_alarm"] = (
            "Alarm" if any(cta != "OK" for cta in self.telesignalization.cell_temperature_alarm) else "OK"
        )

         # 20-Bit alarms

        bit_alarm_fields = {
            'alarm_event_1': {
                'offset': 29,
                'sensors': [
                    { 'name': 'voltage_sensing_failure', 'mode': 'fault_normal', 'first_bit': 0 },
                    { 'name': 'temperature_sensing_failure', 'mode': 'fault_normal', 'first_bit': 1 },
                    { 'name': 'current_sensing_failure', 'mode': 'fault_normal', 'first_bit': 2 },
                    { 'name': 'power_switch_failure', 'mode': 'fault_normal', 'first_bit': 3 },
                    { 'name': 'cell_voltage_difference_sensing_failure', 'mode': 'fault_normal', 'first_bit': 4 },
                    { 'name': 'charging_switch_failure', 'mode': 'fault_normal', 'first_bit': 5 },
                    { 'name': 'discharging_switch_failure', 'mode': 'fault_normal', 'first_bit': 6 },
                    { 'name': 'current_limit_switch_failure', 'mode': 'fault_normal', 'first_bit': 7 }
                ]
            },
            'alarm_event_2': {
                'offset': 30,
                'sensors': [
                    { 'name': 'cell_overvoltage', 'mode': 'protection_alarm_normal', 'first_bit': 0, 'second_bit': 1 },
                    { 'name': 'cell_voltage_low', 'mode': 'protection_alarm_normal', 'first_bit': 2, 'second_bit': 3 },
                    { 'name': 'pack_overvoltage', 'mode': 'protection_alarm_normal', 'first_bit': 4, 'second_bit': 5 },
                    { 'name': 'pack_voltage_low', 'mode': 'protection_alarm_normal', 'first_bit': 6, 'second_bit': 7 }
                ]
            },
            'alarm_event_3': {
                'offset': 31,
                'sensors': [
                    { 'name': 'charging_temperature_high', 'mode': 'protection_alarm_normal', 'first_bit': 0, 'second_bit': 1 },
                    { 'name': 'charging_temperature_low', 'mode': 'protection_alarm_normal', 'first_bit': 2, 'second_bit': 3 },
                    { 'name': 'discharging_temperature_high', 'mode': 'protection_alarm_normal', 'first_bit': 4, 'second_bit': 5 },
                    { 'name': 'discharging_temperature_low', 'mode': 'protection_alarm_normal', 'first_bit': 6, 'second_bit': 7 }
                ]
            },
            'alarm_event_4': {
                'offset': 32,
                'sensors': [
                    { 'name': 'ambient_temperature_high', 'mode': 'protection_alarm_normal', 'first_bit': 0, 'second_bit': 1 },
                    { 'name': 'ambient_temperature_low', 'mode': 'protection_alarm_normal', 'first_bit': 2, 'second_bit': 3 },
                    { 'name': 'component_temperature_high', 'mode': 'protection_alarm_normal', 'first_bit': 4, 'second_bit': 5 },
                    { 'name': 'low_temperature_heating', 'mode': 'on_off', 'first_bit': 6 }
                ]
            },
            'alarm_event_5': {
                'offset': 33,
                'sensors': [
                    { 'name': 'charging_overcurrent', 'mode': 'protection_alarm_normal', 'first_bit': 0, 'second_bit': 1 },
                    { 'name': 'discharging_overcurrent', 'mode': 'protection_alarm_normal', 'first_bit': 2, 'second_bit': 3 },
                    { 'name': 'transient_overcurrent', 'mode': 'lockout_protection_normal', 'first_bit': 4, 'second_bit': 5 },
                    { 'name': 'output_short_circuit', 'mode': 'lockout_protection_normal', 'first_bit': 6, 'second_bit': 7 }
                ]
            },
            'alarm_event_6': {
                'offset': 34,
                'sensors': [
                    { 'name': 'charging_high_voltage_protection', 'mode': 'protection_normal', 'first_bit': 0 },
                    { 'name': 'intermittent_power_supplement', 'mode': 'warning_normal', 'first_bit': 1 },
                    { 'name': 'soc_low', 'mode': 'protection_alarm_normal', 'first_bit': 2, 'second_bit': 3 },
                    { 'name': 'cell_low_voltage_forbidden_charging', 'mode': 'protection_normal', 'first_bit': 4 },
                    { 'name': 'output_reverse_polarity_protection', 'mode': 'protection_normal', 'first_bit': 5 },
                    { 'name': 'output_connection_failure', 'mode': 'fault_normal', 'first_bit': 6 }
                ]
            },
            'switch_status': {
                'offset': 35,
                'sensors': [
                    { 'name': 'discharge_switch', 'mode': 'on_off', 'first_bit': 0 },
                    { 'name': 'charge_switch', 'mode': 'on_off', 'first_bit': 1 },
                    { 'name': 'current_limit_switch', 'mode': 'on_off', 'first_bit': 2 },
                    { 'name': 'heating_switch', 'mode': 'on_off', 'first_bit': 3 }
                ]
            },
            'balancer_1':  {
                'offset': 36,
                'sensors': [
                    { 'name': 'balancer_cell', 'mode': 'on_off', 'first_bit': 0, 'amount': 8 }
                ]
            },
            'balancer_2':  {
                'offset': 37,
                'sensors': [
                    { 'name': 'balancer_cell', 'mode': 'on_off', 'first_bit': 0, 'amount': 8, "start": 8 }
                ]
            },
            'system_status': {
                'offset': 38,
                'sensors': [
                    { 'name': 'Discharging', 'mode': 'on_off', 'first_bit': 0 },
                    { 'name': 'Charging', 'mode': 'on_off', 'first_bit': 1 },
                    { 'name': 'Floating Charge', 'mode': 'on_off', 'first_bit': 2 },
                    { 'name': 'Standby', 'mode': 'on_off', 'first_bit': 4 },
                    { 'name': 'Off', 'mode': 'on_off', 'first_bit': 5 }
                ]
            },
            'disconnection_1':  {
                'offset': 39,
                'sensors': [
                    { 'name': 'disconnection_cell', 'mode': 'warning_normal', 'first_bit': 0, 'amount': 8 }
                ]
            },
            'disconnection_2':  {
                'offset': 40,
                'sensors': [
                    { 'name': 'disconnection_cell', 'mode': 'warning_normal', 'first_bit': 0, 'amount': 8, "start": 8 }
                ]
            },
            'alarm_event_7': {
                'offset': 41,
                'sensors': [
                    { 'name': 'auto_charging_wait', 'mode': 'warning_normal', 'first_bit': 4 },
                    { 'name': 'manual_charging_wait', 'mode': 'warning_normal', 'first_bit': 5 }
                ]
            },
            'alarm_event_8': {
                'offset': 42,
                'sensors': [
                    { 'name': 'eep_storage_failure', 'mode': 'fault_normal', 'first_bit': 0 },
                    { 'name': 'rtc_clock_failure', 'mode': 'fault_normal', 'first_bit': 1 },
                    { 'name': 'no_calibration_of_voltage', 'mode': 'warning_normal', 'first_bit': 2 },
                    { 'name': 'no_calibration_of_current', 'mode': 'warning_normal', 'first_bit': 3 },
                    { 'name': 'no_calibration_of_null_point', 'mode': 'warning_normal', 'first_bit': 4 }
                ]
            }
        }

        ## Fetch values for all bit_alarm fields
        for group, cfg in bit_alarm_fields.items():
            offset = cfg["offset"]
            sensors = cfg["sensors"]

            for sensor in sensors:
                name       = sensor.get("name")
                mode       = sensor.get("mode")
                first_bit  = sensor.get("first_bit", 0)
                second_bit = sensor.get("second_bit")
                amount     = sensor.get("amount", 1)
                start      = sensor.get("start", 0)

                #### Binary-sensors only
                if amount > 1:
                    arr = getattr(self.telesignalization, name)

                    for i in range(amount):
                        bit = first_bit + i
                        value = self.status_from_20_bit_alarm(
                            data,
                            offset,
                            mode=mode,
                            first_bit=bit
                        )
                        idx = start + i
                        arr[idx] = value
                        
                        ### Add to telesignalization_feedback
                        feedback_binary[f"{name}_{idx + 1}"] = value
                #### Normal- and binary-sensors
                else:
                    value = self.status_from_20_bit_alarm(
                        data,
                        offset,
                        mode=mode,
                        first_bit=first_bit,
                        second_bit=second_bit
                    )
                    if group == "system_status": # Special handling of system-status
                        if value == "ON":
                            setattr(self.telesignalization, group, name)
                    else:
                        setattr(self.telesignalization, name, value)

                    ### Add to telesignalization_feedback
                    if group == "system_status": # Special handling of system-status
                        feedback_normal[group] = name
                    else:
                        if mode in ("protection_alarm_normal", "lockout_protection_normal"):
                            feedback_normal[name] = value
                        else:
                            feedback_binary[name] = value

        return telesignalization_feedback

    def _request_feedback_frame(
        self,
        cid2: int,
        expected_length: int,
        decoder: Callable[[bytes], Dict[str, Any]],
        frame_label: str
    ) -> Optional[Dict[str, Any]]:
        """Request a feedback frame (telemetry or telesignalization) with retry/validation."""
        if not app_state.serial_instance:
            logger.error("Serial instance not initialized")
            return None

        command = self.encode_cmd(address=self.pack_address, cid2=cid2)
        logger.debug("Pack%s:%s_command: %s", self.pack_address, frame_label, command)

        for attempt in range(self.FRAME_READ_RETRIES):
            app_state.serial_instance.write(command)
            raw_data = app_state.serial_instance.read_until(b'\r')

            if len(raw_data) < self.FRAME_MIN_LENGTH:
                logger.debug(
                    "Pack%s:%s attempt %s: insufficient length",
                    self.pack_address,
                    frame_label,
                    attempt + 1
                )
                continue

            
            pack_address_data = raw_data[3:-77]
            info_frame_data = raw_data[13:-5]

            if (
                self.is_valid_hex_string(pack_address_data) and
                self.int_from_1byte_hex_ascii(pack_address_data, 0) == self.pack_address and
                self.is_valid_length(info_frame_data, expected_length=expected_length) and
                self.is_valid_hex_string(info_frame_data) and
                self.is_valid_frame(raw_data)
            ):
                feedback = decoder(info_frame_data)
                feedback_dump = json.dumps(feedback, indent=2)
                logger.info("Pack%s:%s received", self.pack_address, frame_label)
                logger.debug(
                    "Pack%s:%s: %s",
                    self.pack_address,
                    frame_label,
                    feedback_dump
                )
                return feedback

            logger.debug(
                "Pack%s:%s attempt %s: validation failed",
                self.pack_address,
                frame_label,
                attempt + 1
            )

        logger.error(
            "Pack%s:Failed to read %s after %s retries",
            self.pack_address,
            frame_label.lower(),
            self.FRAME_READ_RETRIES
        )
        return None

    def read_serial_data(self) -> Optional[BatteryData]:
        """Read data for battery pack from serial interface."""
        logger.info("Pack%s:Requesting data...", self.pack_address)

        if not app_state.serial_instance:
            logger.error("Serial instance not initialized")
            return None

        battery_pack_data = {
            "telemetry": {},
            "telesignalization": {}
        }

        try:
            # Flush serial buffers
            app_state.serial_instance.flushOutput()
            app_state.serial_instance.flushInput()

            # Request telemetry data
            telemetry_feedback = self._request_feedback_frame(
                cid2=0x42,
                expected_length=150,
                decoder=self.decode_telemetry_feedback_frame,
                frame_label="Telemetry"
            )
            if telemetry_feedback is None:
                return None
            battery_pack_data["telemetry"] = telemetry_feedback

            # Mandatory delay between each request or there will be corrupt data
            time.sleep(1)

            # Request telesignalization data
            telesignalization_feedback = self._request_feedback_frame(
                cid2=0x44,
                expected_length=98,
                decoder=self.decode_telesignalization_feedback_frame,
                frame_label="Telesignalization"
            )
            if telesignalization_feedback is None:
                return None
            battery_pack_data["telesignalization"] = telesignalization_feedback

            # Check if data has changed
            if self.last_status is None or self.last_status != battery_pack_data:
                self.last_status = battery_pack_data
                return battery_pack_data

            return None
        except Exception as e:
            logger.error("Pack%s:Error reading serial data: %s", self.pack_address, e)
            return None


def on_mqtt_connect(
    client: mqtt.Client,
    _userdata: Any,
    _flags: Any,
    reason_code: int,
    _properties=None
) -> None:
    """Handle MQTT connection."""
    if reason_code == 0:
        logger.info(
            "Connected to MQTT broker (%s:%s)",
            Config.MQTT_HOST,
            Config.MQTT_PORT
        )
        if Config.ENABLE_HA_DISCOVERY_CONFIG:
            client.subscribe(f"{Config.HA_DISCOVERY_PREFIX}/status")
            logger.info(
                "Subscribed to %s/status for HA discovery",
                Config.HA_DISCOVERY_PREFIX
            )
    else:
        logger.error("Failed to connect to MQTT broker: %s", reason_code)


def on_ha_online(client: mqtt.Client, _userdata: Any, message: mqtt.MQTTMessage) -> None:
    """Handle Home Assistant online status - republish sensor configs."""
    try:
        payload = message.payload.decode('utf-8')
        if payload == "online":
            logger.info("Home Assistant online, sending sensor configs")
            auto_discovery = AutoDiscoveryConfig(
                mqtt_topic=Config.MQTT_TOPIC,
                discovery_prefix=Config.HA_DISCOVERY_PREFIX,
                invert_ha_dis_charge_measurements=Config.INVERT_HA_DIS_CHARGE_MEASUREMENTS,
                mqtt_client=client
            )
            for pack in app_state.battery_packs:
                auto_discovery.create_autodiscovery_sensors(pack_no=pack['address'])
    except Exception as e:
        logger.error("Error handling HA online status: %s", e)


def initialize_mqtt() -> mqtt.Client:
    """Initialize and connect MQTT client."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)
    client.on_connect = on_mqtt_connect
    client.will_set(f"{Config.MQTT_TOPIC}/availability", payload="offline", qos=2, retain=False)

    if Config.ENABLE_HA_DISCOVERY_CONFIG:
        client.on_message = on_ha_online

    try:
        client.connect(Config.MQTT_HOST, Config.MQTT_PORT, keepalive=60)
        client.loop_start()
        return client
    except MQTTException as e:
        logger.error("MQTT connection failed: %s", e)
        sys.exit(1)


def initialize_serial() -> serial.Serial:
    """Initialize serial connection."""
    try:
        baudrate = 9600 if Config.NUMBER_OF_PACKS > 1 else 19200
        logger.info(
            "Initializing serial interface %s at %s baud",
            Config.SERIAL_INTERFACE,
            baudrate
        )
        return serial.Serial(
            port=Config.SERIAL_INTERFACE,
            baudrate=baudrate,
            timeout=0.5
        )
    except SerialException as e:
        logger.error("Serial initialization failed: %s", e)
        sys.exit(1)


def main():
    """Main application loop."""
    try:
        # Initialize MQTT
        app_state.mqtt_client = initialize_mqtt()

        # Initialize Serial
        app_state.serial_instance = initialize_serial()

        # Initialize battery packs
        app_state.battery_packs.clear()
        for i in range(Config.NUMBER_OF_PACKS):
            pack_instance = SeplosBatteryPack(pack_address=i)
            app_state.battery_packs.append({
                "pack_instance": pack_instance,
                "address": i
            })
        logger.info("Initialized %s battery pack(s)", Config.NUMBER_OF_PACKS)

        # Send Home Assistant Auto-Discovery configurations on startup
        if Config.ENABLE_HA_DISCOVERY_CONFIG:
            logger.info("Sending Home Assistant Auto-Discovery configurations")
            auto_discovery = AutoDiscoveryConfig(
                mqtt_topic=Config.MQTT_TOPIC,
                discovery_prefix=Config.HA_DISCOVERY_PREFIX,
                invert_ha_dis_charge_measurements=Config.INVERT_HA_DIS_CHARGE_MEASUREMENTS,
                mqtt_client=app_state.mqtt_client
            )
            for pack in app_state.battery_packs:
                auto_discovery.create_autodiscovery_sensors(pack_no=pack['address'])
            logger.info("Auto-Discovery configurations sent")

        # Main loop
        pack_index = 0
        while True:
            try:
                current_pack = app_state.battery_packs[pack_index]
                pack_instance = current_pack["pack_instance"]
                pack_address = current_pack["address"]

                # Fetch battery pack data
                pack_data = pack_instance.read_serial_data()

                if pack_data:
                    # Publish updated data to MQTT
                    logger.info("Pack%s:Publishing updated data to MQTT", pack_address)
                    topic = f"{Config.MQTT_TOPIC}/pack-{pack_address}/sensors"
                    payload = {**pack_data}
                    app_state.mqtt_client.publish(topic, json.dumps(payload, indent=2))
                else:
                    logger.info("Pack%s:No changes detected", pack_address)

                # Publish availability
                app_state.mqtt_client.publish(f"{Config.MQTT_TOPIC}/availability", "online", retain=False)

                # Mandatory delay between each request or there will be corrupt data
                time.sleep(1)

                # Move to next pack
                pack_index += 1
                if pack_index >= len(app_state.battery_packs):
                    pack_index = 0
                    if Config.MQTT_UPDATE_INTERVAL > 0:
                        logger.info(
                            "Waiting %s seconds before next cycle",
                            Config.MQTT_UPDATE_INTERVAL
                        )
                        time.sleep(Config.MQTT_UPDATE_INTERVAL)

            except Exception as e:
                logger.error("Error in main loop: %s", e)
                time.sleep(10)

    except KeyboardInterrupt:
        logger.info("Shutdown requested via keyboard interrupt")
    except Exception as e:
        logger.error("Fatal error: %s", e)
    finally:
        graceful_exit()


if __name__ == "__main__":
    main()
