import sys
import os
import logging
import configparser
import time
import json
import serial
from serial.serialutil import SerialException
import paho.mqtt.client as mqtt
from paho.mqtt import MQTTException
from typing import List

try:
    # Logging
    logging.basicConfig()
    logger = logging.getLogger("SeplosBMS")

    # Cast config vars to requested type
    def cast_value(value, return_type):
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

    # Get config vars either from env-var (1st) or config.ini (2nd)
    def get_config_value(var_name, return_type=str):
        # First, try to get the value from environment variables
        value = os.environ.get(var_name)
        if value is not None:
            return cast_value(value, return_type)

        # If the variable is not in the environment, try the config file
        config = configparser.ConfigParser()
        config.read("config.ini")

        for section in config.sections():
            if var_name in config[section]:
                return cast_value(config[section][var_name], return_type)

        # Return None if the variable is not found
        return None

    # BMS config
    # When ONLY_MASTER is True, data will only be fetched for one pack (0) 
    ONLY_MASTER = get_config_value("ONLY_MASTER", return_type=bool)
    # When ONLY_MASTER is False, data will be fetched for NUMBER_OF_PACKS (1-n)
    NUMBER_OF_PACKS = get_config_value("NUMBER_OF_PACKS", return_type=int)
    # Set min and max cell-voltage as this cannot be read from the BMS
    MIN_CELL_VOLTAGE = get_config_value("MIN_CELL_VOLTAGE", return_type=float)
    MAX_CELL_VOLTAGE = get_config_value("MAX_CELL_VOLTAGE", return_type=float)

    # Logging config
    if get_config_value("LOGGING_LEVEL").upper() == "ERROR":
        logger.setLevel(logging.ERROR)
    elif get_config_value("LOGGING_LEVEL").upper() == "WARNING":
        logger.setLevel(logging.WARNING)
    elif get_config_value("LOGGING_LEVEL").upper() == "DEBUG":
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # MQTT config

    MQTT_HOST = get_config_value("MQTT_HOST")
    MQTT_PORT = get_config_value("MQTT_PORT", return_type=int)
    MQTT_USERNAME = get_config_value("MQTT_USERNAME")
    MQTT_PASSWORD = get_config_value("MQTT_PASSWORD")
    MQTT_TOPIC = get_config_value("MQTT_TOPIC")
    MQTT_UPDATE_INTERVAL = get_config_value("MQTT_UPDATE_INTERVAL", return_type=int)

    # Setup MQTT client
    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = logger.info("mqtt connected ({}:{}, user: {})".format(MQTT_HOST, MQTT_PORT, MQTT_USERNAME))

    # Serial Interface config, set to 9600 for Master and 19200 for Slaves

    SERIAL_INTERFACE = get_config_value("SERIAL_INTERFACE")
    SERIAL_BAUD_RATE = get_config_value("SERIAL_BAUD_RATE", return_type=int)

    # Variable for global serial instance
    serial_instance = None

    # Now you can use these variables in your code
    logger.debug(f"SERIAL_INTERFACE: {SERIAL_INTERFACE}")
    logger.debug(f"SERIAL_BAUD_RATE: {SERIAL_BAUD_RATE}")

    logger.debug(f"MQTT_HOST: {MQTT_HOST}")
    logger.debug(f"MQTT_PORT: {MQTT_PORT}")
    logger.debug(f"MQTT_USERNAME: {MQTT_USERNAME}")
    logger.debug(f"MQTT_PASSWORD: {MQTT_PASSWORD}")
    logger.debug(f"MQTT_TOPIC: {MQTT_TOPIC}")

    logger.debug(f"ONLY_MASTER: {ONLY_MASTER}")
    logger.debug(f"NUMBER_OF_PACKS: {NUMBER_OF_PACKS}")

    logger.debug(f"MIN_CELL_VOLTAGE: {MIN_CELL_VOLTAGE}")
    logger.debug(f"MAX_CELL_VOLTAGE: {MAX_CELL_VOLTAGE}")

    class Protection(object):
        """
        This class holds Warning and alarm states for different types of Checks
        They are of type integer, 2 represents an Alarm, 1 a Warning, 0 if everything is fine
        """

        ALARM = 2
        WARNING = 1
        OK = 0

        def __init__(self):
            self.voltage_high: int = None
            self.voltage_low: int = None
            
            self.voltage_cell_low: int = None
            self.voltage_cell_high: int = None

            self.soc_low: int = None
            
            self.current_over: int = None
            self.current_under: int = None
            
            self.temp_high_charge: int = None
            self.temp_low_charge: int = None
            
            self.temp_high_discharge: int = None
            self.temp_low_discharge: int = None

    class Cell:
        def __init__(self, voltage):
            self.voltage = voltage

    class SeplosBatteryPack():
        def __init__(self, battery_pack_address):
            self.initialized = False
            self.last_status = None

            self.battery_pack_address = battery_pack_address
            
            self.voltage = None
            self.current = None
            self.port_voltage = None

            self.capacity_rated = None
            self.capacity = None
            self.capacity_remain = None
            self.soc = None
            self.soh = None
            
            self.cycles = None
            
            self.env_temp = None
            self.pwr_temp = None
            
            self.cell_count = None
            self.cells: List[Cell] = []
            self.min_pack_voltage = None
            self.max_pack_voltage = None
            self.lowest_cell = None
            self.highest_cell = None
            
            self.protection = Protection()
            self.alarm_status = None
            self.discharge_fet_enabled = None
            self.charge_fet_enabled = None

        # return integer from given 1 byte ascii hex data
        @staticmethod
        def int_from_1byte_hex_ascii(data: bytes, offset: int, signed=False):
            return int.from_bytes(
                bytes.fromhex(data[offset : offset + 2].decode("ascii")),
                byteorder="big",
                signed=signed,
            )

        # return integer from given 2 byte ascii hex data
        @staticmethod
        def int_from_2byte_hex_ascii(data: bytes, offset: int, signed=False):
            return int.from_bytes(
                bytes.fromhex(data[offset : offset + 4].decode("ascii")),
                byteorder="big",
                signed=signed,
            )

        # calculate given frame checksum
        @staticmethod
        def get_checksum(frame: bytes) -> int:
            """implements the Seplos checksum algorithm, returns 4 bytes"""
            checksum = 0
            for b in frame:
                checksum += b
            checksum %= 0xFFFF
            checksum ^= 0xFFFF
            checksum += 1
            return checksum

        # check ascii data is hex only
        @staticmethod
        def is_valid_hex_string(data) -> bool:
            try:
                bytes.fromhex(data.decode("ascii"))
                logger.debug("frame has hex only ok")
                return True
            except ValueError:
                logger.debug("frame includes non-hexadecimal characters, got {}".format(data))
                return False
        
        # check data has requested length
        @staticmethod
        def is_valid_length(data, expected_length: int) -> bool:
            # check frame length (alarm: 98, stats: 168)
            datalength = len(data)
            if datalength < expected_length:
                logger.debug("frame length too short, got {}, data {}".format(datalength, data))
                return False
            logger.debug("frame length ok, got {}".format(datalength))
            
            return True
        
        @staticmethod
        def decode_alarm_byte(data_byte: int, alarm_bit: int, warn_bit: int):
            if data_byte & (1 << alarm_bit) != 0:
                return Protection.ALARM
            if data_byte & (1 << warn_bit) != 0:
                return Protection.WARNING
            return Protection.OK

        def decode_alarm_data(self, data: bytes):
            alarm_data = {}
            
            voltage_alarm_byte = bytes.fromhex(data.decode("ascii"))[30]
            temperature_alarm_byte = bytes.fromhex(data.decode("ascii"))[31]
            current_alarm_byte = bytes.fromhex(data.decode("ascii"))[33]
            soc_alarm_byte = bytes.fromhex(data.decode("ascii"))[34]
            switch_byte = bytes.fromhex(data.decode("ascii"))[35]

            self.protection.voltage_cell_low = self.decode_alarm_byte(
                data_byte=voltage_alarm_byte, alarm_bit=3, warn_bit=2
            )
            alarm_data["voltage_cell_low"] = self.protection.voltage_cell_low

            self.protection.voltage_cell_high = self.decode_alarm_byte(
                data_byte=voltage_alarm_byte, alarm_bit=1, warn_bit=0
            )
            alarm_data["voltage_cell_high"] = self.protection.voltage_cell_high

            self.protection.voltage_low = self.decode_alarm_byte(
                data_byte=voltage_alarm_byte, alarm_bit=7, warn_bit=6
            )
            alarm_data["voltage_low"] = self.protection.voltage_low

            self.protection.voltage_high = self.decode_alarm_byte(
                data_byte=voltage_alarm_byte, alarm_bit=5, warn_bit=4
            )
            alarm_data["voltage_high"] = self.protection.voltage_high
            
            self.protection.temp_low_charge = self.decode_alarm_byte(
                data_byte=temperature_alarm_byte, alarm_bit=3, warn_bit=2
            )
            alarm_data["temp_low_charge"] = self.protection.temp_low_charge

            self.protection.temp_high_charge = self.decode_alarm_byte(
                data_byte=temperature_alarm_byte, alarm_bit=1, warn_bit=0
            )
            alarm_data["temp_high_charge"] = self.protection.temp_high_charge

            self.protection.temp_low_discharge = self.decode_alarm_byte(
                data_byte=temperature_alarm_byte, alarm_bit=7, warn_bit=6
            )
            alarm_data["temp_low_discharge"] = self.protection.temp_low_discharge

            self.protection.temp_high_discharge = self.decode_alarm_byte(
                data_byte=temperature_alarm_byte, alarm_bit=5, warn_bit=4
            )
            alarm_data["temp_high_discharge"] = self.protection.temp_high_discharge

            self.protection.current_over = self.decode_alarm_byte(
                data_byte=current_alarm_byte, alarm_bit=1, warn_bit=0
            )
            alarm_data["current_over"] = self.protection.current_over

            self.protection.current_under = self.decode_alarm_byte(
                data_byte=current_alarm_byte, alarm_bit=3, warn_bit=2
            )
            alarm_data["current_under"] = self.protection.current_under

            self.protection.soc_low = self.decode_alarm_byte(
                data_byte=soc_alarm_byte, alarm_bit=3, warn_bit=2
            )
            alarm_data["soc_low"] = self.protection.soc_low

            self.discharge_fet_enabled = True if switch_byte & 0b01 != 0 else False
            alarm_data["discharge_fet_enabled"] = self.discharge_fet_enabled

            self.charge_fet_enabled = True if switch_byte & 0b10 != 0 else False
            alarm_data["charge_fet_enabled"] = self.charge_fet_enabled

            logger.info("Alarm Voltage Cell low = {}".format(self.protection.voltage_cell_low))
            logger.info("Alarm Voltage Cell high = {}".format(self.protection.voltage_cell_high))
                
            logger.info("Alarm Voltage low = {}".format(self.protection.voltage_low))
            logger.info("Alarm Voltage high = {}".format(self.protection.voltage_high))
                
            logger.info("Alarm Temp low charge = {}".format(self.protection.temp_low_charge))
            logger.info("Alarm Temp high charge = {}".format(self.protection.temp_high_charge))

            logger.info("Alarm Temp low discharge = {}".format(self.protection.temp_low_discharge))
            logger.info("Alarm Temp high discharge = {}".format(self.protection.temp_high_discharge))
                
            logger.info("Alarm Current over = {}".format(self.protection.current_over))
            logger.info("Alarm Current under = {}".format(self.protection.current_under))
                
            logger.info("Alarm SoC low = {}".format(self.protection.soc_low))

            logger.info("Discharge FET enabled = {}".format(self.discharge_fet_enabled))
            logger.info("Discharge FET enabled = {}".format(self.charge_fet_enabled))

            return alarm_data

        # check validity of given frame, i.e. lenght, checksum and error flag
        def is_valid_frame(self, data: bytes) -> bool:
            """checks if data contains a valid frame
            * minimum length is 18 Byte
            * checksum needs to be valid
            * also checks for error code as return code in cid2
            * not checked: lchksum
            """
            try:
                # check frame checksum
                chksum = self.get_checksum(data[1:-5])
                compare = self.int_from_2byte_hex_ascii(data, -5)
                if chksum != compare:
                    logger.debug("frame has wrong checksum, got {}, expected {}".format(chksum, compare))
                    return False
                logger.debug("frame checksum ok, got {}, expected {}".format(chksum, compare))

                # check frame cid2 flag
                cid2 = data[7:9]
                if cid2 != b"00":
                    logger.debug("frame error flag (cid2) set, got {}, expected b'00'".format(cid2))
                    return False
                logger.debug("frame error flag (cid2) ok, got {}".format(cid2))

                return True

            # catch corrupted frames
            except UnicodeError:
                logger.debug("frame corrupted, got {}".format(data))
                return False
            # catch non-hexadecimal numbers
            except ValueError:
                logger.debug("frame has non-hexadecimal number, got {}".format(data))
                return False

        # calculate info length checksum
        @staticmethod
        def get_info_length(info: bytes) -> int:
            """implements the Seplos checksum for the info length"""
            lenid = len(info)
            if lenid == 0:
                return 0

            lchksum = (lenid & 0xF) + ((lenid >> 4) & 0xF) + ((lenid >> 8) & 0xF)
            lchksum %= 16
            lchksum ^= 0xF
            lchksum += 1

            return (lchksum << 12) + lenid

        # calculate command to send for each battery_pack using its address
        def encode_cmd(self, address: int, cid2: int = 0x42, info: bytes = b"01") -> bytes:
            """encodes a command sent to a battery (cid1=0x46)"""
            cid1 = 0x46

            info_length = self.get_info_length(info)

            frame = "{:02X}{:02X}{:02X}{:02X}{:04X}".format(
                0x20, address, cid1, cid2, info_length
            ).encode()
            frame += info

            checksum = self.get_checksum(frame)
            encoded = b"~" + frame + "{:04X}".format(checksum).encode() + b"\r"
            return encoded
        
        # get cell with the lowest voltage
        def get_min_cell(self) -> int:
            min_voltage = 9999
            min_cell = None
            if len(self.cells) == 0 and hasattr(self, "cell_min_no"):
                return self.cell_min_no

            for c in range(min(len(self.cells), self.cell_count)):
                if (
                    self.cells[c].voltage is not None
                    and min_voltage > self.cells[c].voltage
                ):
                    min_voltage = self.cells[c].voltage
                    min_cell = c
            return min_cell

        # get cell with the highest voltage
        def get_max_cell(self) -> int:
            max_voltage = 0
            max_cell = None
            if len(self.cells) == 0 and hasattr(self, "cell_max_no"):
                return self.cell_max_no

            for c in range(min(len(self.cells), self.cell_count)):
                if (
                    self.cells[c].voltage is not None
                    and max_voltage < self.cells[c].voltage
                ):
                    max_voltage = self.cells[c].voltage
                    max_cell = c
            return max_cell

        # init cells array for the battery
        def init_battery(self):
            # After successful connection init_battery will be called to set up the battery.
            # Set the current limits, populate cell count, etc.
            # Return True if success, False for failure

            self.min_pack_voltage = MIN_CELL_VOLTAGE * self.cell_count
            self.max_pack_voltage = MAX_CELL_VOLTAGE * self.cell_count

            # init the cell array
            for _ in range(self.cell_count):
                self.cells.append(Cell(False))

            return True
        
        # decode battery_pack data
        def decode_status_data(self, data):
                status_data = {}

                # data offsets
                cell_count_offset = 4
                cell_voltage_offset = 6
                temps_offset = 72
                current_offset = 96
                voltage_offset = 100
                capacity_remain_offset = 104
                capacity_offset = 110
                soc_offset = 114
                capacity_rated_offset = 118
                cycles_offset = 122
                soh_offset = 126
                port_voltage_offset = 130

                # fetch cell count
                self.cell_count = self.int_from_1byte_hex_ascii(
                    data=data, offset=cell_count_offset
                )

                # setup the battery on first run after cell count is known
                if not self.initialized:
                    self.init_battery()
                    self.initialized = True

                # fetch cell-voltages and temps
                if self.cell_count == len(self.cells):
                    # get voltages for each cell
                    for i in range(self.cell_count):
                        voltage = (
                            self.int_from_2byte_hex_ascii(data, cell_voltage_offset + i * 4) / 1000
                        )
                        self.cells[i].voltage = voltage
                        tmp_key = f"cell_{i}_voltage"
                        status_data[tmp_key] = voltage
                        
                        logger.info("Voltage Cell[{}]={}V".format(i, voltage))
                    
                    # get highest and lowest cell
                    self.lowest_cell = self.get_min_cell()
                    self.highest_cell = self.get_max_cell()
                    status_data["lowest_cell"] = self.lowest_cell
                    status_data["highest_cell"] = self.highest_cell

                    logger.info("Lowest Cell[{}]".format(self.lowest_cell ))
                    logger.info("Highest Cell[{}]".format(self.highest_cell))

                    # get values for the 4 existing cell-temperature sensors
                    for i in range(0, 4):
                        temp = (
                            self.int_from_2byte_hex_ascii(data, temps_offset + i * 4) - 2731
                        ) / 10
                        self.cells[i].temp = temp
                        tmp_key = f"cell_temp_{i}"
                        status_data[tmp_key] = temp

                        logger.info("Temp Cell[{}]={}°C".format(i, temp))
                
                # fetch env-temp
                self.env_temp = (self.int_from_2byte_hex_ascii(data, temps_offset + 4 * 4) - 2731) / 10
                status_data["env_temp"] = self.env_temp

                # fetch pwr-temp
                self.pwr_temp = (self.int_from_2byte_hex_ascii(data, temps_offset + 5 * 4) - 2731) / 10
                status_data["pwr_temp"] = self.pwr_temp

                # fetch current
                self.current = self.int_from_2byte_hex_ascii(data, current_offset, signed=True) / 100
                status_data["current"] = self.current

                # fetch voltage
                self.voltage = self.int_from_2byte_hex_ascii(data, voltage_offset) / 100
                status_data["voltage"] = self.voltage
                
                # fetch rated capacity
                self.capacity_rated = self.int_from_2byte_hex_ascii(data, capacity_rated_offset) / 100
                status_data["capacity_rated"] = self.capacity_rated

                # fetch capacity
                self.capacity = self.int_from_2byte_hex_ascii(data, capacity_offset) / 100
                status_data["capacity"] = self.capacity

                # fetch remaining capacity
                self.capacity_remain = self.int_from_2byte_hex_ascii(data, capacity_remain_offset) / 100
                status_data["capacity_remain"] = self.capacity_remain
                
                # fetch soc
                self.soc = self.int_from_2byte_hex_ascii(data, soc_offset) / 10
                status_data["soc"] = self.soc
                
                # fetch cycles
                self.cycles = self.int_from_2byte_hex_ascii(data, cycles_offset)
                status_data["cycles"] = self.cycles

                # fetch soh
                self.soh = self.int_from_2byte_hex_ascii(data, soh_offset) / 10
                status_data["soh"] = self.soh

                # fetch port voltage
                self.port_voltage = self.int_from_2byte_hex_ascii(data, port_voltage_offset) / 100
                status_data["port_voltage"] = self.port_voltage
                
                logger.info("Current = {}A".format(self.current))
                logger.info("Voltage = {}V".format(self.voltage))
                logger.info("Port Voltage = {}V".format(self.port_voltage))

                logger.info("Rated Capacity = {}Ah".format(self.capacity_rated))
                logger.info("Capacity = {}Ah".format(self.capacity))
                logger.info("Remaining Capacity = {}Ah".format(self.capacity_remain))

                logger.info("SOC = {}%".format(self.soc))
                logger.info("SOH = {}%".format(self.soh))

                logger.info("Cycles = {}".format(self.cycles))

                logger.info("Environment temp = {}°C".format(self.env_temp))
                logger.info("Power temp = {}°C".format(self.pwr_temp))

                return status_data

        # read data for given battery_pack address from serial interface
        def read_serial_data(self, serial_instance):
            logger.info("Fetch data for battery_pack {}".format(self.battery_pack_address))

            # json object to store status and alarm response values
            battery_pack_data = {
                "status": {},
                "alarm": {}
            }
            
            # flush interface in- and output
            serial_instance.flushOutput()
            serial_instance.flushInput()

            # calculate request command for the current battery_pack_address
            command = self.encode_cmd(self.battery_pack_address)
            logger.debug("info-request command: {}".format(command))

            # loop over responses until a valid frame is received, then decode and return it
            iteration_a = 1
            while True:
                # send the command to the serial port until a response is received
                if iteration_a == 1 or iteration_a % 5 == 0:
                    serial_instance.write(command)
                
                # set EOL to \r
                raw_data = serial_instance.read_until(b'\r')
                data = raw_data[13 : -5]

                # check if data is valid frame
                if self.is_valid_length(data, expected_length=150) and self.is_valid_hex_string and self.is_valid_frame(raw_data):
                    logger.info("Battery-Pack {} stats:".format(self.battery_pack_address))
                    status_data = self.decode_status_data(data)
                    battery_pack_data["status"] = status_data
                    break

            # calculate request command for the current battery_pack_address
            command = self.encode_cmd(self.battery_pack_address, cid2=0x44)
            logger.debug("alert-request command: {}".format(command))

            # loop over responses until a valid frame is received, then decode and return it
            iteration_b = 1
            while True:
                # send the command to the serial port until a response is received
                if iteration_b == 1 or iteration_b % 5 == 0:
                    serial_instance.write(command)
                
                # set EOL to \r
                raw_data = serial_instance.read_until(b'\r')
                data = raw_data[13 : -5]

                # check if data is valid frame
                if self.is_valid_length(data, expected_length=98) and self.is_valid_hex_string and self.is_valid_frame(raw_data):
                    logger.info("Battery-Pack {} alarm status:".format(self.battery_pack_address))
                    alarm_data = self.decode_alarm_data(data)
                    battery_pack_data["alarm"] = alarm_data
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
        mqtt_client.loop_start()
    except MQTTException as e:
        logger.error(f"MQTTException occurred: {e}")
        sys.exit(1)

    # connect serial interface
    try:
        serial_instance = serial.Serial(SERIAL_INTERFACE, SERIAL_BAUD_RATE)
    except SerialException as e:
        logger.error(f"SerialException occurred: {e}")
        sys.exit(1)

    # array of battery-pack objects
    battery_packs = []

    # fill battery_packs array with one (ONLY_MASTER = true) or multiple pack(s)
    if ONLY_MASTER:
        battery_packs.append({"address": 0, "instance": SeplosBatteryPack(0)})
    else:
        for i in range(1, NUMBER_OF_PACKS + 1):
            address = int(f'0x{i:02x}', 16)
            instance = SeplosBatteryPack(address)
            battery_packs.append({"address": address, "instance": instance})

    # fetch battery-pack stats and alarm data
    i = 0
    while True:
        current_battery_pack = battery_packs[i]["instance"]
        stats = current_battery_pack.read_serial_data(serial_instance)
        
        if stats:
            logger.debug("JSON stats: {}".format(stats))

            logger.info("Sending stats to MQTT")
            topic = f"{MQTT_TOPIC}/pack-{i + 1 if not ONLY_MASTER else 0}/sensors"
            mqtt_client.publish(topic, json.dumps(stats, indent=4))
        else:
            logger.info("Stats have not changed. No update required.")

        # query all packs again after defined time
        i += 1
        if i >= len(battery_packs):
            time.sleep(MQTT_UPDATE_INTERVAL)
            i = 0

except KeyboardInterrupt:
    logger.info("Interrupt received! Cleaning up...")

finally:
    # close mqtt client if connected
    if mqtt_client.is_connected:
        logger.info("disconnecting mqtt client")
        mqtt_client.disconnect()
        mqtt_client.loop_stop()

    # close serial connection if open
    if serial_instance:
        logger.info("Closing serial connection")
        serial_instance.close()
    logger.info("Exiting the program.")
    sys.exit(0)
