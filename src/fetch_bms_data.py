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
from typing import Optional, Dict, Any, Union, List
import serial
from serial.serialutil import SerialException
import paho.mqtt.client as mqtt
from paho.mqtt import MQTTException
from ha_auto_discovery import AutoDiscoveryConfig

# Type aliases for clarity
ConfigValue = Union[int, float, bool, str, None]
BatteryData = Dict[str, Any]

# Global variables for cleanup
mqtt_client: Optional[mqtt.Client] = None
SERIAL_INSTANCE: Optional[serial.Serial] = None
logger: Optional[logging.Logger] = None


def graceful_exit(signum: Optional[int] = None, frame: Optional[Any] = None) -> None:
    """Handle script exit to disconnect MQTT gracefully and cleanup."""
    global mqtt_client, SERIAL_INSTANCE, logger

    try:
        # Close MQTT client if connected
        if mqtt_client and mqtt_client.is_connected():
            if logger:
                logger.info("Sending offline status to MQTT")
            mqtt_client.publish(f"{os.getenv('MQTT_TOPIC', 'seplos')}/availability", "offline", retain=True)
            if logger:
                logger.info("Disconnecting MQTT client")
            mqtt_client.disconnect()
            mqtt_client.loop_stop()

        # Close serial connections if open
        if SERIAL_INSTANCE and SERIAL_INSTANCE.isOpen():
            if logger:
                logger.info("Closing serial connection")
            SERIAL_INSTANCE.close()
    except Exception as e:
        if logger:
            logger.error(f"Error during graceful exit: {e}")

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
logger.debug(f"Configuration loaded: {vars(Config)}")


class Telesignalization:
    """Holds warning, protection, normal, on and off states for different alarms."""

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

        # System status
        self.system_status: Optional[str] = None

        # Equalization status
        self.cell_balancer: List[Optional[str]] = [None] * 16

        # Disconnection status
        self.cell_disconnection: List[Optional[str]] = [None] * 16


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


class SeplosBatteryPack:
    """Handles all methods for fetching, validating and parsing BMS data."""

    FRAME_READ_RETRIES = 5
    FRAME_MIN_LENGTH = 81
    STATUS_MAP_24 = {
        0: "OK",
        1: "Alarm (low)",
        2: "Alarm (high)"
    }
    SIMPLE_MODE_MAP = {
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
            logger.debug(f"Frame includes non-hexadecimal characters: {data}")
            return False

    @staticmethod
    def is_valid_length(data: bytes, expected_length: int) -> bool:
        """Check if given data matches expected length."""
        actual_length = len(data)
        if actual_length != expected_length:
            logger.debug(f"Frame length mismatch - expected: {expected_length}, got: {actual_length}")
            return False
        logger.debug(f"Frame length OK: {expected_length}")
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
        return SeplosBatteryPack.STATUS_MAP_24.get(alarm_type, "Alarm (other)")

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
        if mode in SeplosBatteryPack.SIMPLE_MODE_MAP:
            active, inactive = SeplosBatteryPack.SIMPLE_MODE_MAP[mode]
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
                logger.debug(f"Frame checksum mismatch - got: {chksum}, expected: {expected}")
                return False
            logger.debug(f"Frame checksum OK: {chksum}")

            # Check frame cid2 flag
            cid2 = data[7:9]
            if cid2 != b"00":
                logger.debug(f"Frame error flag (cid2) set - expected b'00', got: {cid2}")
                return False
            logger.debug(f"Frame error flag OK: {cid2}")

            return True

        except (UnicodeDecodeError, ValueError) as e:
            logger.debug(f"Frame validation error: {e}")
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

        # Number of cells
        number_of_cells = self.int_from_1byte_hex_ascii(data, offset=4)

        # Data offsets
        offsets = {
            'cell_voltage': 6,
            'temps': 72,
            'dis_charge_current': 96,
            'total_pack_voltage': 100,
            'residual_capacity': 104,
            'battery_capacity': 110,
            'state_of_charge': 114,
            'rated_capacity': 118,
            'charging_cycles': 122,
            'state_of_health': 126,
            'port_voltage': 130
        }

        # Set/calculate min/max values
        self.telemetry.min_cell_voltage = Config.MIN_CELL_VOLTAGE
        self.telemetry.max_cell_voltage = Config.MAX_CELL_VOLTAGE
        self.telemetry.min_pack_voltage = Config.MIN_CELL_VOLTAGE * number_of_cells
        self.telemetry.max_pack_voltage = Config.MAX_CELL_VOLTAGE * number_of_cells
        ## Add to telemetry_feedback
        telemetry_feedback["normal"].update({
            "min_cell_voltage": self.telemetry.min_cell_voltage,
            "max_cell_voltage": self.telemetry.max_cell_voltage,
            "min_pack_voltage": self.telemetry.min_pack_voltage,
            "max_pack_voltage": self.telemetry.max_pack_voltage
        })

        # Get cell voltages
        for i in range(number_of_cells):
            self.telemetry.cell_voltage[i] = self.int_from_2byte_hex_ascii(data, offsets['cell_voltage'] + i * 4) / 1000
            ## Add to telemetry_feedback
            telemetry_feedback["normal"][f"voltage_cell_{i + 1}"] = self.telemetry.cell_voltage[i]

        # Calculate average cell voltage
        avg_voltage = sum(self.telemetry.cell_voltage) / number_of_cells
        self.telemetry.average_cell_voltage = round(avg_voltage, 3)
        ## Add to telemetry_feedback
        telemetry_feedback["normal"]["average_cell_voltage"] = self.telemetry.average_cell_voltage

        # Get lowest/highest cells and calculate delta
        lowest_data = self.get_lowest_cell()
        highest_data = self.get_highest_cell()
        self.telemetry.lowest_cell = lowest_data['lowest_cell']
        self.telemetry.lowest_cell_voltage = lowest_data['lowest_cell_voltage']
        self.telemetry.highest_cell = highest_data['highest_cell']
        self.telemetry.highest_cell_voltage = highest_data['highest_cell_voltage']
        self.telemetry.delta_cell_voltage = round(highest_data['highest_cell_voltage'] - lowest_data['lowest_cell_voltage'], 3)
        ## Add to telemetry_feedback
        telemetry_feedback["normal"].update({
            "lowest_cell": self.telemetry.lowest_cell + 1,  # 1-indexed for display
            "lowest_cell_voltage": self.telemetry.lowest_cell_voltage,
            "highest_cell": self.telemetry.highest_cell + 1,  # 1-indexed for display
            "highest_cell_voltage": self.telemetry.highest_cell_voltage,
            "delta_cell_voltage": self.telemetry.delta_cell_voltage
        })

        # Get temperature values
        for i in range(4):
            temp = (self.int_from_2byte_hex_ascii(data, offsets['temps'] + i * 4) - 2731) / 10
            self.telemetry.cell_temperature[i] = temp
            ## Add to telemetry_feedback
            telemetry_feedback["normal"][f"cell_temperature_{i + 1}"] = temp

        # Calculate cell temperature delta
        self.telemetry.delta_cell_temperature = round(max(self.telemetry.cell_temperature) - min(self.telemetry.cell_temperature), 1)
        ## Add to telemetry_feedback
        telemetry_feedback["normal"]["delta_cell_temperature"] = self.telemetry.delta_cell_temperature

        # Get other sensor values
        self.telemetry.ambient_temperature = (self.int_from_2byte_hex_ascii(data, offsets['temps'] + 16) - 2731) / 10
        self.telemetry.components_temperature = (self.int_from_2byte_hex_ascii(data, offsets['temps'] + 20) - 2731) / 10
        self.telemetry.dis_charge_current = self.int_from_2byte_hex_ascii(data, offsets['dis_charge_current'], signed=True) / 100
        self.telemetry.total_pack_voltage = self.int_from_2byte_hex_ascii(data, offsets['total_pack_voltage']) / 100
        self.telemetry.dis_charge_power = round(self.telemetry.dis_charge_current * self.telemetry.total_pack_voltage, 3)
        self.telemetry.rated_capacity = self.int_from_2byte_hex_ascii(data, offsets['rated_capacity']) / 100
        self.telemetry.battery_capacity = self.int_from_2byte_hex_ascii(data, offsets['battery_capacity']) / 100
        self.telemetry.residual_capacity = self.int_from_2byte_hex_ascii(data, offsets['residual_capacity']) / 100
        self.telemetry.state_of_charge = self.int_from_2byte_hex_ascii(data, offsets['state_of_charge']) / 10
        self.telemetry.charging_cycles = self.int_from_2byte_hex_ascii(data, offsets['charging_cycles'])
        self.telemetry.state_of_health = self.int_from_2byte_hex_ascii(data, offsets['state_of_health']) / 10
        self.telemetry.port_voltage = self.int_from_2byte_hex_ascii(data, offsets['port_voltage']) / 100

        # Add all values to feedback
        telemetry_feedback["normal"].update({
            "ambient_temperature": self.telemetry.ambient_temperature,
            "components_temperature": self.telemetry.components_temperature,
            "dis_charge_current": self.telemetry.dis_charge_current,
            "total_pack_voltage": self.telemetry.total_pack_voltage,
            "dis_charge_power": self.telemetry.dis_charge_power,
            "rated_capacity": self.telemetry.rated_capacity,
            "battery_capacity": self.telemetry.battery_capacity,
            "residual_capacity": self.telemetry.residual_capacity,
            "state_of_charge": self.telemetry.state_of_charge,
            "charging_cycles": self.telemetry.charging_cycles,
            "state_of_health": self.telemetry.state_of_health,
            "port_voltage": self.telemetry.port_voltage,
            "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        return telemetry_feedback

    def decode_telesignalization_feedback_frame(self, data: bytes) -> Dict[str, Any]:
        """Decode battery pack telesignalization feedback frame."""
        telesignalization_feedback = {"normal": {}, "binary": {}}

        # Number of cells
        number_of_cells = bytes.fromhex(data.decode("ascii"))[2]

        # 24-Byte alarm offsets
        offsets_24_byte_alarms = {
            'cell_alarm': 3,
            'cell_temperature_alarm': 20,
            'ambient_temperature_alarm': 24,
            'component_temperature_alarm': 25,
            'dis_charge_current_alarm': 26,
            'pack_voltage_alarm': 27
        }

        # Cell voltage alarms
        for i in range(number_of_cells):
            status = self.status_from_24_byte_alarm(data, offsets_24_byte_alarms['cell_alarm'] + i)
            self.telesignalization.cell_voltage_alarm[i] = status
            telesignalization_feedback["normal"][f"cell_voltage_alarm_{i + 1}"] = status
        ## General cell voltage alarm if any of the cells has an active alarm
        telesignalization_feedback["normal"]["any_cell_voltage_alarm"] = (
            "Alarm" if any(s != "OK" for s in self.telesignalization.cell_voltage_alarm) else "OK"
        )

        # Cell temperature alarms
        for i in range(4):
            status = self.status_from_24_byte_alarm(data, offsets_24_byte_alarms['cell_temperature_alarm'] + i)
            self.telesignalization.cell_temperature_alarm[i] = status
            telesignalization_feedback["normal"][f"cell_temperature_alarm_{i + 1}"] = status
        ## General cell temperature alarm if any of the cells has an active alarm
        telesignalization_feedback["normal"]["any_cell_temperature_alarm"] = (
            "Alarm" if any(s != "OK" for s in self.telesignalization.cell_temperature_alarm) else "OK"
        )

        # 24-byte alarms
        byte_alarm_config = [
            ('ambient_temperature_alarm', offsets_24_byte_alarms['ambient_temperature_alarm']),
            ('component_temperature_alarm', offsets_24_byte_alarms['component_temperature_alarm']),
            ('dis_charging_current_alarm', offsets_24_byte_alarms['dis_charge_current_alarm']),
            ('pack_voltage_alarm', offsets_24_byte_alarms['pack_voltage_alarm'])
        ]

        for name, offset in byte_alarm_config:
            status = self.status_from_24_byte_alarm(data, offset)
            setattr(self.telesignalization, name, status)
            telesignalization_feedback["normal"][name] = status

        # 20-Bit alarm offsets
        offsets_20_bit_alarms = {
            'alarm_event_1': 29,
            'alarm_event_2': 30,
            'alarm_event_3': 31,
            'alarm_event_4': 32,
            'alarm_event_5': 33,
            'alarm_event_6': 34,
            'on_off_state': 35,
            'balancer_1': 36,
            'balancer_2': 37,
            'system_status': 38,
            'disconnection_1': 39,
            'disconnection_2': 40,
            'alarm_event_7': 41,
            'alarm_event_8': 42
        }

        # 20-bit alarms
        bit_alarm_config = {
            'alarm_event_1': [
                ('voltage_sensing_failure', 'fault_normal', 0),
                ('temperature_sensing_failure', 'fault_normal', 1),
                ('current_sensing_failure', 'fault_normal', 2),
                ('power_switch_failure', 'fault_normal', 3),
                ('cell_voltage_difference_sensing_failure', 'fault_normal', 4),
                ('charging_switch_failure', 'fault_normal', 5),
                ('discharging_switch_failure', 'fault_normal', 6),
                ('current_limit_switch_failure', 'fault_normal', 7)
            ],
            'alarm_event_2': [
                ('cell_overvoltage', 'protection_alarm_normal', 0, 1),
                ('cell_voltage_low', 'protection_alarm_normal', 2, 3),
                ('pack_overvoltage', 'protection_alarm_normal', 4, 5),
                ('pack_voltage_low', 'protection_alarm_normal', 6, 7)
            ],
            'alarm_event_3': [
                ('charging_temperature_high', 'protection_alarm_normal', 0, 1),
                ('charging_temperature_low', 'protection_alarm_normal', 2, 3),
                ('discharging_temperature_high', 'protection_alarm_normal', 4, 5),
                ('discharging_temperature_low', 'protection_alarm_normal', 6, 7)
            ],
            'alarm_event_4': [
                ('ambient_temperature_high', 'protection_alarm_normal', 0, 1),
                ('ambient_temperature_low', 'protection_alarm_normal', 2, 3),
                ('component_temperature_high', 'protection_alarm_normal', 4, 5),
                ('low_temperature_heating', 'on_off', 6)
            ],
            'alarm_event_5': [
                ('charging_overcurrent', 'protection_alarm_normal', 0, 1),
                ('discharging_overcurrent', 'protection_alarm_normal', 2, 3),
                ('transient_overcurrent', 'lockout_protection_normal', 4, 6),
                ('output_short_circuit', 'lockout_protection_normal', 5, 7)
            ],
            'alarm_event_6': [
                ('charging_high_voltage_protection', 'protection_normal', 0),
                ('intermittent_power_supplement', 'warning_normal', 1),
                ('soc_low', 'protection_alarm_normal', 2, 3),
                ('cell_low_voltage_forbidden_charging', 'protection_normal', 4),
                ('output_reverse_polarity_protection', 'protection_normal', 5),
                ('output_connection_failure', 'fault_normal', 6)
            ],
            'alarm_event_7': [
                ('auto_charging_wait', 'warning_normal', 4),
                ('manual_charging_wait', 'warning_normal', 5)
            ],
            'alarm_event_8': [
                ('eep_storage_failure', 'fault_normal', 0),
                ('rtc_clock_failure', 'fault_normal', 1),
                ('no_calibration_of_voltage', 'warning_normal', 2),
                ('no_calibration_of_current', 'warning_normal', 3),
                ('no_calibration_of_null_point', 'warning_normal', 4)
            ]
        }

        for alarm_group, configs in bit_alarm_config.items():
            for config in configs:
                name = config[0]
                mode = config[1]
                first_bit = config[2]
                second_bit = config[3] if len(config) > 3 else None

                status = self.status_from_20_bit_alarm(
                    data,
                    offsets_20_bit_alarms[alarm_group],
                    mode=mode,
                    first_bit=first_bit,
                    second_bit=second_bit
                )
                setattr(self.telesignalization, name, status)
                if mode in ("protection_alarm_normal", "lockout_protection_normal"):
                    telesignalization_feedback["normal"][name] = status
                else:
                    telesignalization_feedback["binary"][name] = status


        # System status
        system_status_bits = [
            ('Discharging', 0),
            ('Charging', 1),
            ('Floating Charge', 2),
            ('Standby', 4),
            ('Off', 5)
        ]

        for name, bit in system_status_bits:
            status = self.status_from_20_bit_alarm(data, offsets_20_bit_alarms['system_status'], mode="on_off", first_bit=bit)
            if status == "ON":
                setattr(self.telesignalization, "system_status", name)
                telesignalization_feedback["normal"]["system_status"] = name


        # Switch status
        switch_status_config = [
            ('discharge_switch', 0),
            ('charge_switch', 1),
            ('current_limit_switch', 2),
            ('heating_switch', 3)
        ]

        for name, bit in switch_status_config:
            status = self.status_from_20_bit_alarm(data, offsets_20_bit_alarms['on_off_state'], mode="on_off", first_bit=bit)
            setattr(self.telesignalization, name, status)
            telesignalization_feedback["binary"][name] = status


        # Equalization status
        for i in range(number_of_cells):
            bit = i % 8
            offset = offsets_20_bit_alarms['balancer_1'] if i < 8 else offsets_20_bit_alarms['balancer_2']
            status = self.status_from_20_bit_alarm(data, offset, mode="on_off", first_bit=bit)
            self.telesignalization.cell_balancer[i] = status
            telesignalization_feedback["binary"][f"balancer_cell_{i + 1}"] = status


        # Disconnection status
        for i in range(number_of_cells):
            bit = i % 8
            offset = offsets_20_bit_alarms['disconnection_1'] if i < 8 else offsets_20_bit_alarms['disconnection_2']
            status = self.status_from_20_bit_alarm(data, offset, mode="warning_normal", first_bit=bit)
            self.telesignalization.cell_disconnection[i] = status
            telesignalization_feedback["binary"][f"disconnection_cell_{i + 1}"] = status

        return telesignalization_feedback

    def _request_feedback_frame(
        self,
        cid2: int,
        expected_length: int,
        decoder: callable,
        frame_label: str
    ) -> Optional[Dict[str, Any]]:
        """Request a feedback frame (telemetry or telesignalization) with retry/validation."""
        if not SERIAL_INSTANCE:
            logger.error("Serial instance not initialized")
            return None

        command = self.encode_cmd(address=self.pack_address, cid2=cid2)
        logger.debug(f"Pack{self.pack_address}:{frame_label}_command: {command}")

        for attempt in range(self.FRAME_READ_RETRIES):
            SERIAL_INSTANCE.write(command)
            raw_data = SERIAL_INSTANCE.read_until(b'\r')

            if len(raw_data) < self.FRAME_MIN_LENGTH:
                logger.debug(f"Pack{self.pack_address}:{frame_label} attempt {attempt + 1}: insufficient length")
                continue

            pack_no_data = raw_data[3:-77]
            info_frame_data = raw_data[13:-5]

            if (
                self.is_valid_hex_string(pack_no_data) and
                self.int_from_1byte_hex_ascii(pack_no_data, 0) == self.pack_address and
                self.is_valid_length(info_frame_data, expected_length=expected_length) and
                self.is_valid_hex_string(info_frame_data) and
                self.is_valid_frame(raw_data)
            ):
                feedback = decoder(info_frame_data)
                logger.info(f"Pack{self.pack_address}:{frame_label} received")
                logger.debug(f"Pack{self.pack_address}:{frame_label}: {json.dumps(feedback, indent=2)}")
                return feedback

            logger.debug(f"Pack{self.pack_address}:{frame_label} attempt {attempt + 1}: validation failed")

        logger.error(f"Pack{self.pack_address}:Failed to read {frame_label.lower()} after {self.FRAME_READ_RETRIES} retries")
        return None

    def read_serial_data(self) -> Optional[BatteryData]:
        """Read data for battery pack from serial interface."""
        logger.info(f"Pack{self.pack_address}:Requesting data...")

        if not SERIAL_INSTANCE:
            logger.error("Serial instance not initialized")
            return None

        battery_pack_data = {
            "telemetry": {},
            "telesignalization": {}
        }

        try:
            # Flush serial buffers
            SERIAL_INSTANCE.flushOutput()
            SERIAL_INSTANCE.flushInput()

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

            # Small delay between requests
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
            logger.error(f"Pack{self.pack_address}:Error reading serial data: {e}")
            return None


def on_mqtt_connect(client: mqtt.Client, userdata: Any, flags: Any, reason_code: int, properties=None) -> None:
    """Handle MQTT connection."""
    if reason_code == 0:
        logger.info(f"Connected to MQTT broker ({Config.MQTT_HOST}:{Config.MQTT_PORT})")
        if Config.ENABLE_HA_DISCOVERY_CONFIG:
            client.subscribe(f"{Config.HA_DISCOVERY_PREFIX}/status")
            logger.info(f"Subscribed to {Config.HA_DISCOVERY_PREFIX}/status for HA discovery")
    else:
        logger.error(f"Failed to connect to MQTT broker: {reason_code}")


def on_ha_online(client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
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
            for pack in battery_packs:
                auto_discovery.create_autodiscovery_sensors(pack_no=pack['address'])
    except Exception as e:
        logger.error(f"Error handling HA online status: {e}")


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
        logger.error(f"MQTT connection failed: {e}")
        sys.exit(1)


def initialize_serial() -> serial.Serial:
    """Initialize serial connection."""
    try:
        baudrate = 9600 if Config.NUMBER_OF_PACKS > 1 else 19200
        logger.info(f"Initializing serial interface {Config.SERIAL_INTERFACE} at {baudrate} baud")
        return serial.Serial(
            port=Config.SERIAL_INTERFACE,
            baudrate=baudrate,
            timeout=0.5
        )
    except SerialException as e:
        logger.error(f"Serial initialization failed: {e}")
        sys.exit(1)


def main():
    """Main application loop."""
    global mqtt_client, SERIAL_INSTANCE, battery_packs

    try:
        # Initialize MQTT
        mqtt_client = initialize_mqtt()
    
        # Initialize Serial
        SERIAL_INSTANCE = initialize_serial()
    
        # Initialize battery packs
        battery_packs = []
        for i in range(Config.NUMBER_OF_PACKS):
            pack_instance = SeplosBatteryPack(pack_address=i)
            battery_packs.append({
                "pack_instance": pack_instance,
                "address": i
            })
        logger.info(f"Initialized {Config.NUMBER_OF_PACKS} battery pack(s)")
    
        # Send Home Assistant Auto-Discovery configurations on startup
        if Config.ENABLE_HA_DISCOVERY_CONFIG:
            logger.info("Sending Home Assistant Auto-Discovery configurations")
            auto_discovery = AutoDiscoveryConfig(
                mqtt_topic=Config.MQTT_TOPIC,
                discovery_prefix=Config.HA_DISCOVERY_PREFIX,
                invert_ha_dis_charge_measurements=Config.INVERT_HA_DIS_CHARGE_MEASUREMENTS,
                mqtt_client=mqtt_client
            )
            for pack in battery_packs:
                auto_discovery.create_autodiscovery_sensors(pack_no=pack['address'])
            logger.info("Auto-Discovery configurations sent")

        # Main loop
        pack_index = 0
        while True:
            try:
                current_pack = battery_packs[pack_index]
                pack_instance = current_pack["pack_instance"]
                pack_address = current_pack["address"]
            
                # Fetch battery pack data
                pack_data = pack_instance.read_serial_data()
            
                if pack_data:
                    # Publish updated data to MQTT
                    logger.info(f"Pack{pack_address}:Publishing updated data to MQTT")
                    topic = f"{Config.MQTT_TOPIC}/pack-{pack_address}/sensors"
                    payload = {**pack_data}
                    mqtt_client.publish(topic, json.dumps(payload, indent=2))
                else:
                    logger.info(f"Pack{pack_address}:No changes detected")
            
                # Publish availability
                mqtt_client.publish(f"{Config.MQTT_TOPIC}/availability", "online", retain=False)
            
                # Small delay to prevent bus collisions
                time.sleep(1)
            
                # Move to next pack
                pack_index += 1
                if pack_index >= len(battery_packs):
                    pack_index = 0
                    if Config.MQTT_UPDATE_INTERVAL > 0:
                        logger.info(f"Waiting {Config.MQTT_UPDATE_INTERVAL} seconds before next cycle")
                        time.sleep(Config.MQTT_UPDATE_INTERVAL)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested via keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        graceful_exit()


if __name__ == "__main__":
    main()
