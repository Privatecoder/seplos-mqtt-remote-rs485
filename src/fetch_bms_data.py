"""
reads one or more seplos protocol v2.0 bms (in parallel) via
(remote) serial connection(s) and publsihes their data to mqtt
"""
import sys
import os
import signal
import logging
import configparser
import time
from datetime import datetime
import json
import serial
from serial.serialutil import SerialException
import paho.mqtt.client as mqtt
from paho.mqtt import MQTTException
from ha_auto_discovery import AutoDiscoveryConfig

try:
    def graceful_exit(signum=None, frame=None):
        """ 
        handle script exit to disconnect mqtt gracefully and cleanup
        """
        # close mqtt client if connected
        if mqtt_client.is_connected():
            logger.info("Sending offline status to mqtt")
            mqtt_client.publish(f"{MQTT_TOPIC}/availability", "offline")
            logger.info("Disconnecting mqtt client")
            mqtt_client.disconnect()
            mqtt_client.loop_stop()

        # close serial connections if open
        if SERIAL_MASTER_INSTANCE is not None:
            logger.info("Closing serial connection to master")
            SERIAL_MASTER_INSTANCE.close()
        if SERIAL_SLAVES_INSTANCE is not None:
            logger.info("Closing serial connection to slaves")
            SERIAL_SLAVES_INSTANCE.close()
        logger.info("Exiting the program.")

        if signum is not None:
            sys.exit(0)

    # register signal handler for SIGTERM
    signal.signal(signal.SIGTERM, graceful_exit)

    def cast_value(value, return_type) -> int | float | bool | str | None:
        """ 
        cast config vars to requested type, i.e. int / float / boolean / string 
        """
        try:
            if return_type == int:
                return int(value)
            elif return_type == float:
                return float(value)
            elif return_type == bool:
                return value.lower() in ['true', '1', 'yes', 'on']
            else:
                return str(value)
        except ValueError:
            return None

    def get_config_value(var_name, return_type=str) -> int | float | bool | str | None:
        """
        get config settings from env (primary) or config.ini (secondary)
        """
        # first, try to get the value from environment variables
        value = os.environ.get(var_name)
        if value is not None:
            return cast_value(value, return_type)

        # if the variable is not in the environment, try the config file
        config = configparser.ConfigParser()
        config.read("config.ini")

        for section in config.sections():
            if var_name in config[section]:
                return cast_value(config[section][var_name], return_type)

        # return None if the variable is not found
        return None

    # BMS config

    # set min and max cell-voltage as this cannot be read from the BMS
    MIN_CELL_VOLTAGE = get_config_value("MIN_CELL_VOLTAGE", return_type=float)
    MAX_CELL_VOLTAGE = get_config_value("MAX_CELL_VOLTAGE", return_type=float)

    # Logging setup and config

    logging.basicConfig()
    logger = logging.getLogger("SeplosBMS")

    if get_config_value("LOGGING_LEVEL").upper() == "ERROR":
        logger.setLevel(logging.ERROR)
    elif get_config_value("LOGGING_LEVEL").upper() == "WARNING":
        logger.setLevel(logging.WARNING)
    elif get_config_value("LOGGING_LEVEL").upper() == "DEBUG":
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # MQTT config and setup

    MQTT_HOST = get_config_value("MQTT_HOST")
    MQTT_PORT = get_config_value("MQTT_PORT", return_type=int)
    MQTT_USERNAME = get_config_value("MQTT_USERNAME")
    MQTT_PASSWORD = get_config_value("MQTT_PASSWORD")
    MQTT_TOPIC = get_config_value("MQTT_TOPIC")
    MQTT_UPDATE_INTERVAL = get_config_value("MQTT_UPDATE_INTERVAL", return_type=int)

    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = logger.info(
        "mqtt connected (%s:%s, user: %s)",
        MQTT_HOST, MQTT_PORT, MQTT_USERNAME
    )

    # Home Assistant auto-discovery config

    ENABLE_HA_DISCOVERY_CONFIG = get_config_value("ENABLE_HA_DISCOVERY_CONFIG", return_type=bool)
    HA_DISCOVERY_PREFIX = get_config_value("HA_DISCOVERY_PREFIX")

    def on_ha_online(client, _userdata, message) -> None:
        """
        home assistant online-status handler, (re-)publishes sensor configs whenever ha goes online
        """
        payload = message.payload.decode('utf-8')
        if payload == "online":
            logger.info("home assistant online, sending sensor configs")
            auto_discovery_instance = AutoDiscoveryConfig(
                mqtt_topic=MQTT_TOPIC,
                discovery_prefix=HA_DISCOVERY_PREFIX,
                mqtt_client=client
            )
            for pack in battery_packs:
                auto_discovery_instance.create_autodiscovery_sensors(pack_no=pack['address'])

    # Serial Interface config and setup (set to 9600 for Master and 19200 for Slaves)

    # fetch master, i.e. pack-0 when FETCH_MASTER == True
    FETCH_MASTER = get_config_value("FETCH_MASTER", return_type=bool)
    # fetch number of slave packs, i.e. number of packs excluding the master
    NUMBER_OF_SLAVES = get_config_value("NUMBER_OF_SLAVES", return_type=int)
    MASTER_SERIAL_INTERFACE = get_config_value("MASTER_SERIAL_INTERFACE")
    SLAVES_SERIAL_INTERFACE = get_config_value("SLAVES_SERIAL_INTERFACE")

    SERIAL_MASTER_INSTANCE = None
    SERIAL_SLAVES_INSTANCE = None

    # Debug output of env-var settings

    logger.debug("MASTER_SERIAL_INTERFACE: %s", MASTER_SERIAL_INTERFACE)
    logger.debug("SLAVES_SERIAL_INTERFACE: %s", SLAVES_SERIAL_INTERFACE)

    logger.debug("MQTT_HOST: %s", MQTT_HOST)
    logger.debug("MQTT_PORT: %s", MQTT_PORT)
    logger.debug("MQTT_USERNAME: %s", MQTT_USERNAME)
    logger.debug("MQTT_PASSWORD: %s", MQTT_PASSWORD)
    logger.debug("MQTT_TOPIC: %s", MQTT_TOPIC)
    logger.debug("MQTT_UPDATE_INTERVAL: %s", MQTT_UPDATE_INTERVAL)
    logger.debug("ENABLE_HA_DISCOVERY_CONFIG: %s", ENABLE_HA_DISCOVERY_CONFIG)

    logger.debug("FETCH_MASTER: %s", FETCH_MASTER)
    logger.debug("NUMBER_OF_SLAVES: %s", NUMBER_OF_SLAVES)

    logger.debug("MIN_CELL_VOLTAGE: %s", MIN_CELL_VOLTAGE)
    logger.debug("MAX_CELL_VOLTAGE: %s", MAX_CELL_VOLTAGE)
    class Telesignalization():
        """
        this class holds warning, protection, normal, on and off states
        for different types of alarms and checks
        """
        def __init__(self):

            # equalization status

            self.cell_voltage_warning = [None] * 16
            self.cell_temperature_warning = [None] * 4
            self.ambient_temperature_warning: str = None
            self.component_temperature_warning: str = None
            self.dis_charging_current_warning: str = None
            self.pack_voltage_warning: str = None

            # warning 1

            self.voltage_sensing_failure: str = None
            self.temp_sensing_failure: str = None
            self.current_sensing_failure: str = None
            self.power_switch_failure: str = None
            self.cell_voltage_difference_sensing_failure: str = None
            self.charging_switch_failure: str = None
            self.discharging_switch_failure: str = None
            self.current_limit_switch_failure: str = None

            # warning 2

            self.cell_overvoltage: str = None
            self.cell_voltage_low: str = None
            self.pack_overvoltage: str = None
            self.pack_voltage_low: str = None

            # warning 3

            self.charging_temp_high: str = None
            self.charging_temp_low: str = None
            self.discharging_temp_high: str = None
            self.discharging_temp_low: str = None

            # warning 4

            self.ambient_temp_high: str = None
            self.ambient_temp_low: str = None
            self.component_temp_high: str = None

            # warning 5

            self.charging_overcurrent: str = None
            self.discharging_overcurrent: str = None
            self.transient_overcurrent: str = None
            self.output_short_circuit: str = None
            self.transient_overcurrent_lock: str = None
            self.output_short_circuit_lock: str = None

            # warning 6

            self.charging_high_voltage: str = None
            self.intermittent_power_supplement: str = None
            self.soc_low: str = None
            self.cell_low_voltage_forbidden_charging: str = None
            self.output_reverse_protection: str = None
            self.output_connection_failure: str = None

            # power status

            self.discharge_switch: str = None
            self.charge_switch: str = None
            self.current_limit_switch: str = None
            self.heating_limit_switch: str = None

            # equalization status

            self.cell_equalization = [None] * 16

            # system status

            self.discharge: str = None
            self.charge: str = None
            self.floating_charge: str = None
            self.standby: str = None
            self.power_off: str = None

            # disconnection status

            self.cell_disconnection = [None] * 16

            # warning 7

            self.auto_charging_wait: str = None
            self.manual_charging_wait: str = None

            # warning 8

            self.eep_storage_failure: str = None
            self.rtc_clock_failure: str = None
            self.no_calibration_of_voltage: str = None
            self.no_calibration_of_current: str = None
            self.no_calibration_of_null_point: str = None

    class Telemetry():
        """
        this class holds numeric states for different sensors
        """
        def __init__(self):

            # from pack

            self.cell_voltage = [None] * 16
            self.cell_temperature: float = [None] * 4
            self.ambient_temperature: float = None
            self.components_temperature: float = None
            self.dis_charge_current: float = None
            self.total_pack_voltage: float = None
            self.residual_capacity: float = None
            self.battery_capacity: float = None
            self.soc: float = None
            self.rated_capacity: float = None
            self.cycles: int = None
            self.soh: float = None
            self.port_voltage: float = None

            # calculated

            self.average_cell_voltage: float = None
            self.delta_cell_voltage: float = None
            self.lowest_cell: int = None
            self.lowest_cell_voltage: float = None
            self.highest_cell: int = None
            self.highest_cell_voltage: float = None
            self.min_pack_voltage: float = None
            self.max_pack_voltage: float = None
            self.dis_charge_power: float = None
    class SeplosBatteryPack():
        """
        this class holds all methods for fetching, validating and parsing data
        """
        def __init__(self, pack_address):

            # pack address (0 for Master, 1-n for Slaves)
            self.pack_address = pack_address

            # last status (update mqtt only on changed data)
            self.last_status = None

            # Telemetry and Telesignalization store
            self.telemetry = Telemetry()           
            self.telesignalization = Telesignalization()

        @staticmethod
        def calculate_frame_checksum(frame: bytes) -> int:
            """
            calculate given frame checksum
            """
            checksum = 0
            for b in frame:
                checksum += b
            checksum %= 0xFFFF
            checksum ^= 0xFFFF
            checksum += 1
            return checksum

        @staticmethod
        def is_valid_hex_string(data) -> bool:
            """
            check if given ascii data is valid hex (only)
            """
            try:
                bytes.fromhex(data.decode("ascii"))
                logger.debug("frame has hex only: ok")
                return True
            except ValueError:
                logger.debug("frame includes non-hexadecimal characters, got: %s", data)
                return False

        @staticmethod
        def is_valid_length(data, expected_length: int) -> bool:
            """
            check if given data is of requested length
            """
            datalength = len(data)
            if datalength != expected_length:
                logger.debug(
                    "frame length too long/short, expected %s, got: %s",
                    expected_length, datalength
                )
                return False
            logger.debug("frame length (expected: %s): ok", expected_length)
            return True

        @staticmethod
        def int_from_1byte_hex_ascii(data: bytes, offset: int, signed=False) -> int:
            """
            return (signed) int value from given 1 byte ascii data
            """
            return int.from_bytes(
                bytes.fromhex(data[offset : offset + 2].decode("ascii")),
                byteorder="big",
                signed=signed,
            )

        @staticmethod
        def int_from_2byte_hex_ascii(data: bytes, offset: int, signed=False) -> int:
            """
            return (signed) int value from given 2 byte ascii data with offset
            """
            return int.from_bytes(
                bytes.fromhex(data[offset : offset + 4].decode("ascii")),
                byteorder="big",
                signed=signed,
            )

        @staticmethod
        def status_from_24_byte_alarm(data: bytes, offset: int) -> str:
            """
            return status as string value from given 24 byte alarm data with offset
            """
            alarm_type = bytes.fromhex(data.decode("ascii"))[offset]
            if alarm_type == 0:
                return "normal"
            elif alarm_type == 1:
                return "trigger_low"
            elif alarm_type == 2:
                return "trigger_high"
            else:
                return "trigger_other"

        @staticmethod
        def status_from_20_bit_alarm(
            data: bytes,
            offset: int,
            on_off_bit: int=None,
            warn_bit: int=None,
            protection_bit: int=None
        ) -> str:
            """
            return status as string value from given 20 bit alarm data with offset
            """
            data_byte = bytes.fromhex(data.decode("ascii"))[offset]
            if on_off_bit is not None:
                return "on" if data_byte & (1 << on_off_bit) != 0 else "off"
            elif warn_bit is not None:
                if data_byte & (1 << warn_bit) != 0:
                    return "warning"
                if protection_bit is not None and data_byte & (1 << protection_bit) != 0:
                    return "protection"
                return "normal"

        def decode_intra_pack_info_frame(self, data) -> None:
            """
            TESTING: print decoded intra battery pack communication frames
            """
            cell_voltage_offset = 4
            print(f"highest_cell_voltage: {self.int_from_2byte_hex_ascii(data, cell_voltage_offset) / 1000}")
            print(f"lowest_cell_voltage: {self.int_from_2byte_hex_ascii(data, cell_voltage_offset + 4) / 1000}")

            temps_offset = 12
            print(f"cells temp 0: {(self.int_from_2byte_hex_ascii(data, temps_offset ) - 2731) / 10}")
            print(f"cells temp 1: {(self.int_from_2byte_hex_ascii(data, temps_offset + 4) - 2731) / 10}")

            dis_charge_current_offset = 20
            print(f"dis_charge_current: {self.int_from_2byte_hex_ascii(data, dis_charge_current_offset, signed=True) / 100}")

            total_pack_voltage_offset = 24
            print(f"total_pack_voltage: {self.int_from_2byte_hex_ascii(data, total_pack_voltage_offset) / 100}")

            residual_capacity_offset = 28
            print(f"residual_capacity: {self.int_from_2byte_hex_ascii(data, residual_capacity_offset) / 100}")

            battery_capacity_offset = 32
            print(f"battery_capacity: {self.int_from_2byte_hex_ascii(data, battery_capacity_offset) / 100}")
            
            soc_offset = 36
            print(f"soc: {self.int_from_2byte_hex_ascii(data, soc_offset) / 10}")

            port_voltage_offset = 40
            print(f"port_voltage: {self.int_from_2byte_hex_ascii(data, port_voltage_offset) / 100}")
            
            #print(f"cell_overvoltage: {self.status_from_20_bit_alarm(data=data[42 : -16], offset=2, warn_bit=1, protection_bit=2)}")
            #print(f"pack_overvoltage: {self.status_from_20_bit_alarm(data=data[42 : -16], offset=2, warn_bit=3, protection_bit=4)}")


        def decode_telesignalization_feedback_frame(self, data: bytes) -> dict:
            """
            return decoded battery pack telesignalization feedback frame
            """
            telesignalization_feedback = {}

            # number of cells

            number_of_cells = bytes.fromhex(data.decode("ascii"))[2]

            # info 24 byte alarm offsets

            cell_warning_byte_offset = 3
            cell_temperature_warning_byte_offset = 20
            ambient_temperature_warning_byte_offset = 24
            component_temperature_warning_byte_offset = 25
            dis_charging_current_warning_byte_offset = 26
            pack_voltage_warning_byte_offset = 27

            # info 20 bit alarm offsets

            warning_1_alarm_byte_offset = 29
            warning_2_alarm_byte_offset = 30
            warning_3_alarm_byte_offset = 31
            warning_4_alarm_byte_offset = 32
            warning_5_alarm_byte_offset = 33
            warning_6_alarm_byte_offset = 34
            power_status_byte_offset = 35
            equalization_status1_byte_offset = 36
            equalization_status2_byte_offset = 37
            system_status_byte_offset = 38
            disconnection_status1_byte_offset = 39
            disconnection_status2_byte_offset = 40
            warning_7_alarm_byte_offset = 41
            warning_8_alarm_byte_offset = 42

            # info data

            for cell in range(0, number_of_cells):  # 0 to 15, for 16 cells
                self.telesignalization.cell_voltage_warning[cell] = self.status_from_24_byte_alarm(data=data, offset=cell_warning_byte_offset + cell)
                telesignalization_feedback[f"voltage_warning_cell_{cell + 1}"] = self.telesignalization.cell_voltage_warning[cell]

            for temp in range(0, 4):  # 0 to 3, for 4 temperature sensors
                self.telesignalization.cell_temperature_warning[temp] = self.status_from_24_byte_alarm(data=data, offset=cell_temperature_warning_byte_offset + temp)
                telesignalization_feedback[f"cell_temperature_warning_{temp + 1}"] = self.telesignalization.cell_temperature_warning[temp]

            self.telesignalization.ambient_temperature_warning = self.status_from_24_byte_alarm(data=data, offset=ambient_temperature_warning_byte_offset)
            telesignalization_feedback["ambient_temperature_warning"] = self.telesignalization.ambient_temperature_warning

            self.telesignalization.component_temperature_warning = self.status_from_24_byte_alarm(data=data, offset=component_temperature_warning_byte_offset)
            telesignalization_feedback["component_temperature_warning"] = self.telesignalization.component_temperature_warning

            self.telesignalization.dis_charging_current_warning = self.status_from_24_byte_alarm(data=data, offset=dis_charging_current_warning_byte_offset)
            telesignalization_feedback["dis_charging_current_warning"] = self.telesignalization.dis_charging_current_warning

            self.telesignalization.pack_voltage_warning = self.status_from_24_byte_alarm(data=data, offset=pack_voltage_warning_byte_offset)
            telesignalization_feedback["pack_voltage_warning"] = self.telesignalization.pack_voltage_warning

            # warning 1

            self.telesignalization.voltage_sensing_failure = self.status_from_20_bit_alarm(
                data=data, offset=warning_1_alarm_byte_offset, warn_bit=0
            )
            telesignalization_feedback["voltage_sensing_failure"] = self.telesignalization.voltage_sensing_failure

            self.telesignalization.temp_sensing_failure = self.status_from_20_bit_alarm(
                data=data, offset=warning_1_alarm_byte_offset, warn_bit=1
            )
            telesignalization_feedback["temp_sensing_failure"] = self.telesignalization.temp_sensing_failure

            self.telesignalization.current_sensing_failure = self.status_from_20_bit_alarm(
                data=data, offset=warning_1_alarm_byte_offset, warn_bit=2
            )
            telesignalization_feedback["current_sensing_failure"] = self.telesignalization.current_sensing_failure

            self.telesignalization.power_switch_failure = self.status_from_20_bit_alarm(
                data=data, offset=warning_1_alarm_byte_offset, warn_bit=3
            )
            telesignalization_feedback["power_switch_failure"] = self.telesignalization.power_switch_failure

            self.telesignalization.cell_voltage_difference_sensing_failure = self.status_from_20_bit_alarm(
                data=data, offset=warning_1_alarm_byte_offset, warn_bit=4
            )
            telesignalization_feedback["cell_voltage_difference_sensing_failure"] = self.telesignalization.cell_voltage_difference_sensing_failure

            self.telesignalization.charging_switch_failure = self.status_from_20_bit_alarm(
                data=data, offset=warning_1_alarm_byte_offset, warn_bit=5
            )
            telesignalization_feedback["charging_switch_failure"] = self.telesignalization.charging_switch_failure

            self.telesignalization.discharging_switch_failure = self.status_from_20_bit_alarm(
                data=data, offset=warning_1_alarm_byte_offset, warn_bit=6
            )
            telesignalization_feedback["discharging_switch_failure"] = self.telesignalization.discharging_switch_failure

            self.telesignalization.current_limit_switch_failure = self.status_from_20_bit_alarm(
                data=data, offset=warning_1_alarm_byte_offset, warn_bit=7
            )
            telesignalization_feedback["current_limit_switch_failure"] = self.telesignalization.current_limit_switch_failure

            # warning 2

            self.telesignalization.cell_overvoltage = self.status_from_20_bit_alarm(
                data=data, offset=warning_2_alarm_byte_offset, warn_bit=0, protection_bit=1
            )
            telesignalization_feedback["cell_overvoltage"] = self.telesignalization.cell_overvoltage

            self.telesignalization.cell_voltage_low = self.status_from_20_bit_alarm(
                data=data, offset=warning_2_alarm_byte_offset, warn_bit=2, protection_bit=3
            )
            telesignalization_feedback["cell_voltage_low"] = self.telesignalization.cell_voltage_low

            self.telesignalization.pack_overvoltage = self.status_from_20_bit_alarm(
                data=data, offset=warning_2_alarm_byte_offset, warn_bit=4, protection_bit=5
            )
            telesignalization_feedback["pack_overvoltage"] = self.telesignalization.pack_overvoltage

            self.telesignalization.pack_voltage_low = self.status_from_20_bit_alarm(
                data=data, offset=warning_2_alarm_byte_offset, warn_bit=6, protection_bit=7
            )
            telesignalization_feedback["pack_voltage_low"] = self.telesignalization.pack_voltage_low

            # warning 3

            self.telesignalization.charging_temp_high = self.status_from_20_bit_alarm(
                data=data, offset=warning_3_alarm_byte_offset, warn_bit=0, protection_bit=1
            )
            telesignalization_feedback["charging_temp_high"] = self.telesignalization.charging_temp_high

            self.telesignalization.charging_temp_low = self.status_from_20_bit_alarm(
                data=data, offset=warning_3_alarm_byte_offset, warn_bit=2, protection_bit=3
            )
            telesignalization_feedback["charging_temp_low"] = self.telesignalization.charging_temp_low

            self.telesignalization.discharging_temp_high = self.status_from_20_bit_alarm(
                data=data, offset=warning_3_alarm_byte_offset, warn_bit=4, protection_bit=5
            )
            telesignalization_feedback["discharging_temp_high"] = self.telesignalization.discharging_temp_high

            self.telesignalization.discharging_temp_low = self.status_from_20_bit_alarm(
                data=data, offset=warning_3_alarm_byte_offset, warn_bit=6, protection_bit=7
            )
            telesignalization_feedback["discharging_temp_low"] = self.telesignalization.discharging_temp_low

            # warning 4

            self.telesignalization.ambient_temp_high = self.status_from_20_bit_alarm(
                data=data, offset=warning_4_alarm_byte_offset, warn_bit=0, protection_bit=1
            )
            telesignalization_feedback["ambient_temp_high"] = self.telesignalization.ambient_temp_high

            self.telesignalization.ambient_temp_low = self.status_from_20_bit_alarm(
                data=data, offset=warning_4_alarm_byte_offset, warn_bit=2, protection_bit=3
            )
            telesignalization_feedback["ambient_temp_high"] = self.telesignalization.ambient_temp_high

            self.telesignalization.component_temp_high = self.status_from_20_bit_alarm(
                data=data, offset=warning_4_alarm_byte_offset, warn_bit=4, protection_bit=5
            )
            telesignalization_feedback["component_temp_high"] = self.telesignalization.component_temp_high

            # warning 5

            self.telesignalization.charging_overcurrent = self.status_from_20_bit_alarm(
                data=data, offset=warning_5_alarm_byte_offset, warn_bit=0, protection_bit=1
            )
            telesignalization_feedback["charging_overcurrent"] = self.telesignalization.charging_overcurrent

            self.telesignalization.discharging_overcurrent = self.status_from_20_bit_alarm(
                data=data, offset=warning_5_alarm_byte_offset, warn_bit=2, protection_bit=3
            )
            telesignalization_feedback["discharging_overcurrent"] = self.telesignalization.discharging_overcurrent

            self.telesignalization.transient_overcurrent = self.status_from_20_bit_alarm(
                data=data, offset=warning_5_alarm_byte_offset, warn_bit=4
            )
            telesignalization_feedback["transient_overcurrent"] = self.telesignalization.transient_overcurrent

            self.telesignalization.output_short_circuit = self.status_from_20_bit_alarm(
                data=data, offset=warning_5_alarm_byte_offset, warn_bit=5
            )
            telesignalization_feedback["output_short_circuit"] = self.telesignalization.output_short_circuit

            self.telesignalization.transient_overcurrent_lock = self.status_from_20_bit_alarm(
                data=data, offset=warning_5_alarm_byte_offset, warn_bit=6
            )
            telesignalization_feedback["transient_overcurrent_lock"] = self.telesignalization.transient_overcurrent_lock

            self.telesignalization.output_short_circuit_lock = self.status_from_20_bit_alarm(
                data=data, offset=warning_5_alarm_byte_offset, warn_bit=7
            )
            telesignalization_feedback["transient_overcurrent_lock"] = self.telesignalization.output_short_circuit_lock

            # warning 6

            self.telesignalization.charging_high_voltage = self.status_from_20_bit_alarm(
                data=data, offset=warning_6_alarm_byte_offset, warn_bit=0
            )
            telesignalization_feedback["charging_high_voltage"] = self.telesignalization.charging_high_voltage

            self.telesignalization.intermittent_power_supplement = self.status_from_20_bit_alarm(
                data=data, offset=warning_6_alarm_byte_offset, warn_bit=1
            )
            telesignalization_feedback["intermittent_power_supplement"] = self.telesignalization.intermittent_power_supplement

            self.telesignalization.soc_low = self.status_from_20_bit_alarm(
                data=data, offset=warning_6_alarm_byte_offset, warn_bit=2, protection_bit=3
            )
            telesignalization_feedback["soc_low"] = self.telesignalization.soc_low

            self.telesignalization.cell_low_voltage_forbidden_charging = self.status_from_20_bit_alarm(
                data=data, offset=warning_6_alarm_byte_offset, warn_bit=4
            )
            telesignalization_feedback["cell_low_voltage_forbidden_charging"] = self.telesignalization.cell_low_voltage_forbidden_charging

            self.telesignalization.output_reverse_protection = self.status_from_20_bit_alarm(
                data=data, offset=warning_6_alarm_byte_offset, warn_bit=5
            )
            telesignalization_feedback["output_reverse_protection"] = self.telesignalization.output_reverse_protection

            self.telesignalization.output_connection_failure = self.status_from_20_bit_alarm(
                data=data, offset=warning_6_alarm_byte_offset, warn_bit=6
            )
            telesignalization_feedback["output_connection_failure"] = self.telesignalization.output_connection_failure

            # power status

            self.telesignalization.discharge_switch = self.status_from_20_bit_alarm(
                data=data, offset=power_status_byte_offset, on_off_bit=0
            )
            telesignalization_feedback["discharge_switch"] = self.telesignalization.discharge_switch

            self.telesignalization.charge_switch = self.status_from_20_bit_alarm(
                data=data, offset=power_status_byte_offset, on_off_bit=1
            )
            telesignalization_feedback["charge_switch"] = self.telesignalization.charge_switch

            self.telesignalization.current_limit_switch = self.status_from_20_bit_alarm(
                data=data, offset=power_status_byte_offset, on_off_bit=2
            )
            telesignalization_feedback["current_limit_switch"] = self.telesignalization.current_limit_switch

            self.telesignalization.heating_limit_switch = self.status_from_20_bit_alarm(
                data=data, offset=power_status_byte_offset, on_off_bit=3
            )
            telesignalization_feedback["heating_limit_switch"] = self.telesignalization.heating_limit_switch

            # equalization status 1 + 2

            for c_es_i in range(0, number_of_cells):
                on_off_bit = c_es_i % 8
                offset = equalization_status1_byte_offset if c_es_i < 8 else equalization_status2_byte_offset

                self.telesignalization.cell_equalization[c_es_i] = self.status_from_20_bit_alarm(
                    data=data, offset=offset, on_off_bit=on_off_bit
                )
                # shift cell-index on return List by 1
                telesignalization_feedback[f"equalization_cell_{c_es_i + 1}"] = self.telesignalization.cell_equalization[c_es_i]

            # system status

            self.telesignalization.discharge = self.status_from_20_bit_alarm(
                data=data, offset=system_status_byte_offset, on_off_bit=0
            )
            telesignalization_feedback["discharge"] = self.telesignalization.discharge

            self.telesignalization.charge = self.status_from_20_bit_alarm(
                data=data, offset=system_status_byte_offset, on_off_bit=1
            )
            telesignalization_feedback["charge"] = self.telesignalization.charge

            self.telesignalization.floating_charge = self.status_from_20_bit_alarm(
                data=data, offset=system_status_byte_offset, on_off_bit=2
            )
            telesignalization_feedback["floating_charge"] = self.telesignalization.floating_charge

            self.telesignalization.standby = self.status_from_20_bit_alarm(
                data=data, offset=system_status_byte_offset, on_off_bit=4
            )
            telesignalization_feedback["standby"] = self.telesignalization.standby

            self.telesignalization.power_off = self.status_from_20_bit_alarm(
                data=data, offset=system_status_byte_offset, on_off_bit=5
            )
            telesignalization_feedback["power_off"] = self.telesignalization.power_off

            # disconnection status 1 + 2

            for c_ds_i in range(0, number_of_cells):
                warn_bit = c_ds_i % 8
                offset = disconnection_status1_byte_offset if c_ds_i < 8 else disconnection_status2_byte_offset

                self.telesignalization.cell_disconnection[c_ds_i] = self.status_from_20_bit_alarm(data=data, offset=offset, warn_bit=warn_bit)
                # shift cell-index on return List by 1
                telesignalization_feedback[f"disconnection_cell_{c_ds_i + 1}"] = self.telesignalization.cell_disconnection[c_ds_i]

            # warning 7

            self.telesignalization.auto_charging_wait = self.status_from_20_bit_alarm(
                data=data, offset=warning_7_alarm_byte_offset, warn_bit=4
            )
            telesignalization_feedback["auto_charging_wait"] = self.telesignalization.auto_charging_wait

            self.telesignalization.manual_charging_wait = self.status_from_20_bit_alarm(
                data=data, offset=warning_7_alarm_byte_offset, warn_bit=5
            )
            telesignalization_feedback["manual_charging_wait"] = self.telesignalization.manual_charging_wait

            # warning 8

            self.telesignalization.eep_storage_failure = self.status_from_20_bit_alarm(
                data=data, offset=warning_8_alarm_byte_offset, warn_bit=0
            )
            telesignalization_feedback["eep_storage_failure"] = self.telesignalization.eep_storage_failure

            self.telesignalization.rtc_clock_failure = self.status_from_20_bit_alarm(
                data=data, offset=warning_8_alarm_byte_offset, warn_bit=1
            )
            telesignalization_feedback["rtc_clock_failure"] = self.telesignalization.rtc_clock_failure

            self.telesignalization.no_calibration_of_voltage = self.status_from_20_bit_alarm(
                data=data, offset=warning_8_alarm_byte_offset, warn_bit=2
            )
            telesignalization_feedback["no_calibration_of_voltage"] = self.telesignalization.no_calibration_of_voltage

            self.telesignalization.no_calibration_of_current = self.status_from_20_bit_alarm(
                data=data, offset=warning_8_alarm_byte_offset, warn_bit=3
            )
            telesignalization_feedback["no_calibration_of_current"] = self.telesignalization.no_calibration_of_current

            self.telesignalization.no_calibration_of_null_point = self.status_from_20_bit_alarm(
                data=data, offset=warning_8_alarm_byte_offset, warn_bit=4
            )
            telesignalization_feedback["no_calibration_of_null_point"] = self.telesignalization.no_calibration_of_null_point

            return telesignalization_feedback

        def is_valid_frame(self, data: bytes) -> bool:
            """
            check validity of given frame, i.e. lenght, checksum and error flag
            * minimum length is 18 Byte
            * checksum needs to be valid
            * cid2 must be 00
            """
            try:
                # check frame checksum
                chksum = self.calculate_frame_checksum(data[1:-5])
                compare = self.int_from_2byte_hex_ascii(data, -5)
                if chksum != compare:
                    logger.debug("frame has wrong checksum, got %s, expected %s", chksum, compare)
                    return False
                logger.debug("frame checksum ok, got %s, expected %s", chksum, compare)

                # check frame cid2 flag
                cid2 = data[7:9]
                if cid2 != b"00":
                    logger.debug("frame error flag (cid2) set, expected expected b'00', got: %s", cid2)
                    return False
                logger.debug("frame error flag (cid2) ok, got: %s", cid2)

                return True

            # catch corrupted frames
            except UnicodeError:
                logger.debug("frame corrupted, got: %s", data)
                return False
            # catch non-hexadecimal numbers
            except ValueError:
                logger.debug("frame has non-hexadecimal number, got: %s", data)
                return False

        @staticmethod
        def get_info_length(info: bytes) -> int:
            """
            calculate info length checksum
            """
            lenid = len(info)
            if lenid == 0:
                return 0

            lchksum = (lenid & 0xF) + ((lenid >> 4) & 0xF) + ((lenid >> 8) & 0xF)
            lchksum %= 16
            lchksum ^= 0xF
            lchksum += 1

            return (lchksum << 12) + lenid

        def encode_cmd(self, address: int, cid2: int = None, info: bytes = b"01") -> bytes:
            """
            encodes command to send for each battery_pack using its address
            """
            cid1 = 0x46

            info_length = self.get_info_length(info)
            frame = f"{0x20:02X}{address:02X}{cid1:02X}{cid2:02X}{info_length:04X}".encode()
            frame += info

            checksum = self.calculate_frame_checksum(frame)
            encoded = b"~" + frame + f"{checksum:04X}".encode() + b"\r"
            return encoded

        def get_lowest_cell(self) -> dict:
            """
            get lowest cell number and its voltage
            """
            lowest_cell = self.telemetry.cell_voltage.index(min(self.telemetry.cell_voltage))
            lowest_cell_voltage = self.telemetry.cell_voltage[lowest_cell]
            return { "lowest_cell": lowest_cell, "lowest_cell_voltage": lowest_cell_voltage }

        def get_highest_cell(self) -> dict:
            """
            get highest cell number and its voltage
            """
            highest_cell = self.telemetry.cell_voltage.index(max(self.telemetry.cell_voltage))
            highest_cell_voltage = self.telemetry.cell_voltage[highest_cell]
            return { "highest_cell": highest_cell, "highest_cell_voltage": highest_cell_voltage }

        def decode_telemetry_feedback_frame(self, data) -> dict:
            """
            return decoded battery pack telemetry feedback frame
            """
            telemetry_feedback = {}

            # number of cells
            number_of_cells = self.int_from_1byte_hex_ascii(data=data, offset=4)

            # data offsets
            cell_voltage_offset = 6
            temps_offset = 72
            dis_charge_current_offset = 96
            total_pack_voltage_offset = 100
            residual_capacity_offset = 104
            battery_capacity_offset = 110
            soc_offset = 114
            rated_capacity_offset = 118
            cycles_offset = 122
            soh_offset = 126
            port_voltage_offset = 130

            # set min and max pack voltage
            telemetry_feedback["min_cell_voltage"] = MIN_CELL_VOLTAGE
            telemetry_feedback["max_cell_voltage"] = MAX_CELL_VOLTAGE

            self.telemetry.min_pack_voltage = MIN_CELL_VOLTAGE * number_of_cells
            self.telemetry.max_pack_voltage = MAX_CELL_VOLTAGE * number_of_cells

            # set min and max pack voltage
            telemetry_feedback["min_pack_voltage"] = self.telemetry.min_pack_voltage
            telemetry_feedback["max_pack_voltage"] = self.telemetry.max_pack_voltage


            # get voltages for each cell
            for c_vol_i in range(number_of_cells):
                voltage = (
                    self.int_from_2byte_hex_ascii(data, cell_voltage_offset + c_vol_i * 4) / 1000
                )
                self.telemetry.cell_voltage[c_vol_i] = voltage
                # shift cell-index on return List by 1
                tmp_key = f"voltage_cell_{c_vol_i + 1}"
                telemetry_feedback[tmp_key] = voltage

            # calculate average cell voltage
            self.telemetry.average_cell_voltage = round((sum(self.telemetry.cell_voltage) / len(self.telemetry.cell_voltage)), 3)
            telemetry_feedback["average_cell_voltage"] = self.telemetry.average_cell_voltage

            # get lowest cell and its voltage
            lowest_cell_data = self.get_lowest_cell()
            self.telemetry.lowest_cell = lowest_cell_data['lowest_cell']
            # shift cell-index on return List by 1
            telemetry_feedback["lowest_cell"] = self.telemetry.lowest_cell + 1
            self.telemetry.lowest_cell_voltage = lowest_cell_data['lowest_cell_voltage']
            telemetry_feedback["lowest_cell_voltage"] = self.telemetry.lowest_cell_voltage

            # get lowest cell and its voltage
            highest_cell_data = self.get_highest_cell()
            self.telemetry.highest_cell = highest_cell_data["highest_cell"]
            # shift cell-index on return List by 1
            telemetry_feedback["highest_cell"] = self.telemetry.highest_cell + 1
            self.telemetry.highest_cell_voltage = highest_cell_data["highest_cell_voltage"]
            telemetry_feedback["highest_cell_voltage"] = self.telemetry.highest_cell_voltage

            # calculate delta cell voltage
            self.telemetry.delta_cell_voltage = round((self.telemetry.highest_cell_voltage - self.telemetry.lowest_cell_voltage), 3)
            telemetry_feedback["delta_cell_voltage"] = self.telemetry.delta_cell_voltage

            # get values for the 4 existing cell-temperature sensors
            for c_temp_i in range(0, 4):
                temp = (self.int_from_2byte_hex_ascii(data, temps_offset + c_temp_i * 4) - 2731) / 10
                self.telemetry.cell_temperature[c_temp_i] = temp
                # shift cell-index on return List by 1
                tmp_key = f"cell_temperature_{c_temp_i + 1}"
                telemetry_feedback[tmp_key] = temp

            # get ambient temperature
            self.telemetry.ambient_temperature = (self.int_from_2byte_hex_ascii(data, temps_offset + 4 * 4) - 2731) / 10
            telemetry_feedback["ambient_temperature"] = self.telemetry.ambient_temperature

            # get components temperature
            self.telemetry.components_temperature = (self.int_from_2byte_hex_ascii(data, temps_offset + 5 * 4) - 2731) / 10
            telemetry_feedback["components_temperature"] = self.telemetry.components_temperature

            # get dis-/charge current
            self.telemetry.dis_charge_current = self.int_from_2byte_hex_ascii(data, dis_charge_current_offset, signed=True) / 100
            telemetry_feedback["dis_charge_current"] = self.telemetry.dis_charge_current

            # get total pack-voltage
            self.telemetry.total_pack_voltage = self.int_from_2byte_hex_ascii(data, total_pack_voltage_offset) / 100
            telemetry_feedback["total_pack_voltage"] = self.telemetry.total_pack_voltage

            # calculate dis-/charge_power
            self.telemetry.dis_charge_power = round((self.telemetry.dis_charge_current * self.telemetry.total_pack_voltage), 3)
            telemetry_feedback["dis_charge_power"] = self.telemetry.dis_charge_power

            # get rated capacity
            self.telemetry.rated_capacity = self.int_from_2byte_hex_ascii(data, rated_capacity_offset) / 100
            telemetry_feedback["rated_capacity"] = self.telemetry.rated_capacity

            # get battery capacity
            self.telemetry.battery_capacity = self.int_from_2byte_hex_ascii(data, battery_capacity_offset) / 100
            telemetry_feedback["battery_capacity"] = self.telemetry.battery_capacity

            # get remaining capacity
            self.telemetry.residual_capacity = self.int_from_2byte_hex_ascii(data, residual_capacity_offset) / 100
            telemetry_feedback["residual_capacity"] = self.telemetry.residual_capacity

            # get soc
            self.telemetry.soc = self.int_from_2byte_hex_ascii(data, soc_offset) / 10
            telemetry_feedback["soc"] = self.telemetry.soc

            # get cycles
            self.telemetry.cycles = self.int_from_2byte_hex_ascii(data, cycles_offset)
            telemetry_feedback["cycles"] = self.telemetry.cycles

            # get soh
            self.telemetry.soh = self.int_from_2byte_hex_ascii(data, soh_offset) / 10
            telemetry_feedback["soh"] = self.telemetry.soh

            # get port voltage
            self.telemetry.port_voltage = self.int_from_2byte_hex_ascii(data, port_voltage_offset) / 100
            telemetry_feedback["port_voltage"] = self.telemetry.port_voltage

            return telemetry_feedback

        def read_serial_data(self):
            """
            read data for given battery_pack address from serial interface
            """
            logger.info("Fetch data for Battery Pack %s", self.pack_address)

            serial_instance = SERIAL_MASTER_INSTANCE if self.pack_address == 0 else SERIAL_SLAVES_INSTANCE

            # json object to store status and alarm response values
            battery_pack_data = {
                "telemetry": {},
                "telesignalization": {}
            }

            # flush interface in- and output
            serial_instance.flushOutput()
            serial_instance.flushInput()

            # TESTING: decode (partly, missing alarm decode and (dis)charge current limits?)
            # if self.pack_address > 0:
            #     while True:
            #         # set EOL to \r
            #         raw_data = serial_instance.read_until(b'\r')
            #         pack_no_data = raw_data[3 : -77]
            #         info_frame_data = raw_data[13 : -5]
                    
            #         is_valid_pack_no = self.is_valid_hex_string(pack_no_data)

            #         if is_valid_pack_no and self.is_valid_length(info_frame_data, expected_length=64) and self.is_valid_hex_string(info_frame_data):
            #             pack_no = self.int_from_1byte_hex_ascii(pack_no_data, 0)
            #             print(f"# pack {pack_no}")
            #             self.decode_intra_pack_info_frame(info_frame_data)
            #             print("----")

            # calculate request telemetry command (0x42) for the current pack_address
            telemetry_command = self.encode_cmd(address=self.pack_address, cid2=0x42)
            logger.debug("telemetry_command: %s", telemetry_command)

            # loop over responses until a valid frame is received, then decode and return it as json
            telemetry_command_iteration = 1
            while True:
                # (re-)send telemetry_command to the serial port until a response is received
                if telemetry_command_iteration == 1 or telemetry_command_iteration % 5 == 0:
                    serial_instance.write(telemetry_command)
                telemetry_command_iteration += 1

                # set EOL to \r
                raw_data = serial_instance.read_until(b'\r')
                # pack address only, strip everything except 1 byte hex ascii
                pack_no_data = raw_data[3 : -77]
                # use info only, i.e. strip soi / ver / adr / cid1 / cid / length / eoi
                info_frame_data = raw_data[13 : -5]

                is_requested_pack = self.is_valid_hex_string(pack_no_data) and self.int_from_1byte_hex_ascii(pack_no_data, 0) == self.pack_address

                # check if data is valid frame
                if is_requested_pack and self.is_valid_length(info_frame_data, expected_length=150) and self.is_valid_hex_string(info_frame_data) and self.is_valid_frame(raw_data):
                    telemetry_feedback = self.decode_telemetry_feedback_frame(info_frame_data)
                    battery_pack_data["telemetry"] = telemetry_feedback
                    logger.info("Battery-Pack %s Telemetry Feedback: %s", self.pack_address, json.dumps(telemetry_feedback, indent=4))
                    break

            # calculate request telesignalization command (0x44) for the current pack_address
            telesignalization_command = self.encode_cmd(address=self.pack_address, cid2=0x44)
            logger.debug("telesignalization_command: %s", telesignalization_command)

            # loop over responses until a valid frame is received, then decode and return it as json
            telesignalization_command_iteration = 1
            while True:
                # (re-)send telesignalization_command to the serial port until a response is received
                if telesignalization_command_iteration == 1 or telesignalization_command_iteration % 5 == 0:
                    serial_instance.write(telesignalization_command)
                telesignalization_command_iteration += 1

                # set EOL to \r
                raw_data = serial_instance.read_until(b'\r')
                # pack address only, strip everything except 1 byte hex ascii
                pack_no_data = raw_data[3 : -77]
                # use info only, i.e. strip soi / ver / adr / cid1 / cid / length / eoi
                info_frame_data = raw_data[13 : -5]

                is_requested_pack = self.is_valid_hex_string(pack_no_data) and self.int_from_1byte_hex_ascii(pack_no_data, 0) == self.pack_address

                # check if data is valid frame
                if is_requested_pack and self.is_valid_length(info_frame_data, expected_length=98) and self.is_valid_hex_string(info_frame_data) and self.is_valid_frame(raw_data):
                    telesignalization_feedback = self.decode_telesignalization_feedback_frame(info_frame_data)
                    battery_pack_data["telesignalization"] = telesignalization_feedback
                    logger.info("Battery-Pack %s Telesignalization feedback: %s", self.pack_address, json.dumps(telesignalization_feedback, indent=4))
                    break

            # keep current stats to check if they changed before returning
            if not self.last_status:
                self.last_status = battery_pack_data
            elif self.last_status == battery_pack_data:
                return False
            else:
                self.last_status = battery_pack_data
            return battery_pack_data

    # connect mqtt client and start the loop
    try:
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        mqtt_client.will_set(f"{MQTT_TOPIC}/availability", payload="offline", qos=2, retain=False)
        mqtt_client.loop_start()
    except MQTTException as e:
        logger.error("MQTTException occurred: %s", e)
        sys.exit(1)

    # connect serial interfaces
    try:
        if FETCH_MASTER is True:
            SERIAL_MASTER_INSTANCE = serial.Serial(port=MASTER_SERIAL_INTERFACE, baudrate=9600)
        SERIAL_SLAVES_INSTANCE = serial.Serial(port=SLAVES_SERIAL_INTERFACE, baudrate=19200)
    except SerialException as e:
        logger.error("SerialException occurred: %s", e)
        sys.exit(1)

    # array of battery-pack objects
    battery_packs = []

    # fill battery_packs array with master- and slave-packs
    if FETCH_MASTER is True:
        battery_packs.append({ "pack_instance": SeplosBatteryPack(pack_address=0), "address": 0 })

    for i in range(1, NUMBER_OF_SLAVES + 1):
        pack_address = int(f'0x{i:02x}', 16)
        pack_instance = SeplosBatteryPack(pack_address=pack_address)
        battery_packs.append({ "pack_instance": pack_instance, "address": pack_address })

    # publish sensor configs to topic (HA_DISCOVERY_PREFIX) when "online"-status is received
    if ENABLE_HA_DISCOVERY_CONFIG is True:
        mqtt_client.subscribe(f"{HA_DISCOVERY_PREFIX}/status")
        mqtt_client.on_message = on_ha_online

    # send stats to mqtt
    logger.info("Sending online status to mqtt")
    mqtt_client.publish(f"{MQTT_TOPIC}/availability", "online")

    # fetch battery-pack Telemetry and Telesignalization data
    i = 0
    while True:
        current_battery_pack = battery_packs[i]["pack_instance"]
        current_address = battery_packs[i]["address"]

        # fetch battery_pack_data
        current_battery_pack_data = current_battery_pack.read_serial_data()

        stats = {}

        # if battery_pack_data has changed, update mqtt stats payload
        if current_battery_pack_data:
            logger.info("Sending updated stats to mqtt")
            stats = {**current_battery_pack_data}
            stats.update({"last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            mqtt_client.publish(f"{MQTT_TOPIC}/pack-{current_address}/sensors", json.dumps(stats, indent=4))

        

        # query all packs again in continuous loop or with pre-defined wait interval after each circular run
        i += 1
        if i >= len(battery_packs):
            time.sleep(MQTT_UPDATE_INTERVAL)
            i = 0

# catch exceptions related to the initial connection to the serial port
except serial.SerialException as e:
    logger.error("Serial port disconnected, exiting...")

# handle keyboard-interruption
except KeyboardInterrupt:
    logger.info("Interrupt received! Cleaning up...")

finally:
    graceful_exit()
