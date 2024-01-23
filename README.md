# Seplos MQTT remote RS485
This is a python script that reads data from one or multiple Seplos (while using CAN to connect to your Inverter) battery packs via a (remote) RS485 connection and publish their stats to MQTT.

## Hardware requirements:

1. (Remote) RS485 device [Waveshare 2-CH RS485 to ETH has been tested](https://www.waveshare.com/2-ch-rs485-to-eth-b.htm)
2. For multiple packs while using CAN to connect to your Inverter, you need a splitter ([this splitter works for me](https://www.amazon.de/gp/product/B00D3KIQXC)) to split the CAN port into CAN+RS485 and two separate RS485 connections (the Waveshare 2-CH RS485 to ETH has two RS485 ports)
3. Something that can run a Docker-Container
4. Seplos BMS [V2 / V16 has been tested](https://www.seplos.com/bms-2.0.html)
5. An MQTT broker

## Connecting serial devices to multiple battery packs

![sample](https://github.com/Privatecoder/seplos-mqtt-remote-rs485/assets/45964815/de37d398-7580-452a-b942-3c374a8b86b6)

## Installation and configuration

1. Configure and setup an MQTT broker with a user and password
2. Configure your (remote) RS485 device, for the Waveshare 2-CH RS485 to ETH this would most importantly be `IP Mode: Static` (must be a reachable IP within your network), `Port: 4196` (default), `Work Mode: TCP Server`, `Transfer Protocol: None`, `Baud Rate: 9600` (for Master with multiple Packs) **or** `Baud Rate: 19200` (for Slaves)
3. Modify the `config.ini` and edit its settings to your needs (**alternatively**: configure everything via ENV-vars)
4. Run the Docker Image, for example like this:

- For the master pack: `docker run -itd -e RS485_REMOTE_IP="192.168.1.200" -e RS485_REMOTE_PORT="4196" -v $(pwd)/config-master.ini:/usr/src/app/config.ini --name seplos-mqtt-master privatecoder/seplos-mqtt-remote-rs485:v1.1.2`

- For the slaves: `docker run -itd -e RS485_REMOTE_IP="192.168.1.201" -e RS485_REMOTE_PORT="4196" -v $(pwd)/config-slaves.ini:/usr/src/app/config.ini --name seplos-mqtt-slaves privatecoder/seplos-mqtt-remote-rs485:v1.1.2`

Available ENV-vars are:

`RS485_REMOTE_IP`
`RS485_REMOTE_PORT`

`MQTT_HOST`
`MQTT_PORT`
`MQTT_USERNAME`
`MQTT_PASSWORD`
`MQTT_TOPIC`
`MQTT_UPDATE_INTERVAL`

`ONLY_MASTER`
`NUMBER_OF_PACKS`
`MIN_CELL_VOLTAGE`
`MAX_CELL_VOLTAGE`

`SERIAL_INTERFACE`
`SERIAL_BAUD_RATE`

`LOGGING_LEVEL`

Set `RS485_REMOTE_IP` and `RS485_REMOTE_PORT` to start the docker image with socat and `vcom0` (used by default).
Not defining them will just start the script (`SERIAL_INTERFACE` must match your existing and passed serial-device).

MQTT messages published by the script will look like this:
```
{
    "telemetry": {
        "min_pack_voltage": 46.4,
        "max_pack_voltage": 55.2,
        "voltage_cell_1": 3.255,
        "voltage_cell_2": 3.255,
        "voltage_cell_3": 3.256,
        "voltage_cell_4": 3.255,
        "voltage_cell_5": 3.253,
        "voltage_cell_6": 3.258,
        "voltage_cell_7": 3.259,
        "voltage_cell_8": 3.256,
        "voltage_cell_9": 3.258,
        "voltage_cell_10": 3.26,
        "voltage_cell_11": 3.255,
        "voltage_cell_12": 3.259,
        "voltage_cell_13": 3.257,
        "voltage_cell_14": 3.263,
        "voltage_cell_15": 3.261,
        "voltage_cell_16": 3.258,
        "average_cell_voltage": 3.257,
        "lowest_cell": 5,
        "lowest_cell_voltage": 3.253,
        "highest_cell": 14,
        "highest_cell_voltage": 3.263,
        "delta_cell_voltage": 0.01,
        "cell_temperature_1": 9.7,
        "cell_temperature_2": 9.1,
        "cell_temperature_3": 9.1,
        "cell_temperature_4": 9.8,
        "ambient_temperature": 14.8,
        "components_temperature": 10.8,
        "dis_charge_current": 0.0,
        "total_pack_voltage": 52.12,
        "dis_charge_power": 0.0,
        "rated_capacity": 280.0,
        "battery_capacity": 280.0,
        "residual_capacity": 44.46,
        "soc": 15.8,
        "cycles": 7,
        "soh": 100.0,
        "port_voltage": 52.14
    },
    "telesignalization": {
        "voltage_warning_cell_1": "normal",
        "voltage_warning_cell_2": "normal",
        "voltage_warning_cell_3": "normal",
        "voltage_warning_cell_4": "normal",
        "voltage_warning_cell_5": "normal",
        "voltage_warning_cell_6": "normal",
        "voltage_warning_cell_7": "normal",
        "voltage_warning_cell_8": "normal",
        "voltage_warning_cell_9": "normal",
        "voltage_warning_cell_10": "normal",
        "voltage_warning_cell_11": "normal",
        "voltage_warning_cell_12": "normal",
        "voltage_warning_cell_13": "normal",
        "voltage_warning_cell_14": "normal",
        "voltage_warning_cell_15": "normal",
        "voltage_warning_cell_16": "normal",
        "cell_temperature_warning_1": "normal",
        "cell_temperature_warning_2": "normal",
        "cell_temperature_warning_3": "normal",
        "cell_temperature_warning_4": "normal",
        "ambient_temperature_warning": "normal",
        "component_temperature_warning": "normal",
        "dis_charging_current_warning": "normal",
        "pack_voltage_warning": "normal",
        "voltage_sensing_failure": "normal",
        "temp_sensing_failure": "normal",
        "current_sensing_failure": "normal",
        "power_switch_failure": "normal",
        "cell_voltage_difference_sensing_failure": "normal",
        "charging_switch_failure": "normal",
        "discharging_switch_failure": "normal",
        "current_limit_switch_failure": "normal",
        "cell_overvoltage": "normal",
        "cell_voltage_low": "normal",
        "pack_overvoltage": "normal",
        "pack_voltage_low": "normal",
        "charging_temp_high": "normal",
        "charging_temp_low": "normal",
        "discharging_temp_high": "normal",
        "discharging_temp_low": "normal",
        "ambient_temp_high": "normal",
        "component_temp_high": "normal",
        "charging_overcurrent": "normal",
        "discharging_overcurrent": "normal",
        "transient_overcurrent": "normal",
        "output_short_circuit": "normal",
        "transient_overcurrent_lock": "normal",
        "charging_high_voltage": "normal",
        "intermittent_power_supplement": "normal",
        "soc_low": "normal",
        "cell_low_voltage_forbidden_charging": "normal",
        "output_reverse_protection": "normal",
        "output_connection_failure": "normal",
        "discharge_switch": "on",
        "charge_switch": "on",
        "current_limit_switch": "off",
        "heating_limit_switch": "off",
        "equalization_cell_1": "off",
        "equalization_cell_2": "off",
        "equalization_cell_3": "off",
        "equalization_cell_4": "off",
        "equalization_cell_5": "off",
        "equalization_cell_6": "off",
        "equalization_cell_7": "off",
        "equalization_cell_8": "off",
        "equalization_cell_9": "off",
        "equalization_cell_10": "off",
        "equalization_cell_11": "off",
        "equalization_cell_12": "off",
        "equalization_cell_13": "off",
        "equalization_cell_14": "off",
        "equalization_cell_15": "off",
        "equalization_cell_16": "off",
        "discharge": "off",
        "charge": "off",
        "floating_charge": "off",
        "standby": "on",
        "power_off": "off",
        "disconnection_cell_1": "normal",
        "disconnection_cell_2": "normal",
        "disconnection_cell_3": "normal",
        "disconnection_cell_4": "normal",
        "disconnection_cell_5": "normal",
        "disconnection_cell_6": "normal",
        "disconnection_cell_7": "normal",
        "disconnection_cell_8": "normal",
        "disconnection_cell_9": "normal",
        "disconnection_cell_10": "normal",
        "disconnection_cell_11": "normal",
        "disconnection_cell_12": "normal",
        "disconnection_cell_13": "normal",
        "disconnection_cell_14": "normal",
        "disconnection_cell_15": "normal",
        "disconnection_cell_16": "normal",
        "auto_charging_wait": "normal",
        "manual_charging_wait": "normal",
        "eep_storage_failure": "normal",
        "rtc_clock_failure": "normal",
        "no_calibration_of_voltage": "normal",
        "no_calibration_of_current": "normal",
        "no_calibration_of_null_point": "normal"
    }
}
```

## Manual execution

1. Clone the project
2. Make sure to have Python v3.10 or later installed
3. Edit `config.ini` in `src` to your needs (to connect your remote RS485 device, bind it for example to `/tmp/vcom0` using socat like `socat pty,link=/tmp/vcom0,raw tcp:192.168.1.200:4196,retry,interval=.2,forever &` or something similar)
4. Run the script, i.e. `python fetch_bms_data.py`

Its output will look like this (`LOGGING` `LEVEL` set to `info`):
```
INFO:SeplosBMS:Battery-Pack 1 Telemetry Feedback: {
    "min_pack_voltage": 46.4,
    "max_pack_voltage": 55.2,
    "voltage_cell_1": 3.255,
    "voltage_cell_2": 3.255,
    "voltage_cell_3": 3.255,
    "voltage_cell_4": 3.255,
    "voltage_cell_5": 3.253,
    "voltage_cell_6": 3.258,
    "voltage_cell_7": 3.259,
    "voltage_cell_8": 3.256,
    "voltage_cell_9": 3.258,
    "voltage_cell_10": 3.261,
    "voltage_cell_11": 3.255,
    "voltage_cell_12": 3.26,
    "voltage_cell_13": 3.257,
    "voltage_cell_14": 3.264,
    "voltage_cell_15": 3.262,
    "voltage_cell_16": 3.259,
    "average_cell_voltage": 3.258,
    "lowest_cell": 5,
    "lowest_cell_voltage": 3.253,
    "highest_cell": 14,
    "highest_cell_voltage": 3.264,
    "delta_cell_voltage": 0.011,
    "cell_temperature_1": 9.7,
    "cell_temperature_2": 9.1,
    "cell_temperature_3": 9.1,
    "cell_temperature_4": 9.8,
    "ambient_temperature": 14.8,
    "components_temperature": 10.8,
    "dis_charge_current": 0.0,
    "total_pack_voltage": 52.12,
    "dis_charge_power": 0.0,
    "rated_capacity": 280.0,
    "battery_capacity": 280.0,
    "residual_capacity": 44.46,
    "soc": 15.8,
    "cycles": 7,
    "soh": 100.0,
    "port_voltage": 52.15
}
INFO:SeplosBMS:Battery-Pack 1 Telesignalization feedback: {
    "warning_cell_1": "normal",
    "warning_cell_2": "normal",
    "warning_cell_3": "normal",
    "warning_cell_4": "normal",
    "warning_cell_5": "normal",
    "warning_cell_6": "normal",
    "warning_cell_7": "normal",
    "warning_cell_8": "normal",
    "warning_cell_9": "normal",
    "warning_cell_10": "normal",
    "warning_cell_11": "normal",
    "warning_cell_12": "normal",
    "warning_cell_13": "normal",
    "warning_cell_14": "normal",
    "warning_cell_15": "normal",
    "warning_cell_16": "normal",
    "warning_cell_temperature_1": "normal",
    "warning_cell_temperature_2": "normal",
    "warning_cell_temperature_3": "normal",
    "warning_cell_temperature_4": "normal",
    "ambient_temperature_warnings": "normal",
    "component_temperature_warnings": "normal",
    "dis_charging_current_warnings": "normal",
    "pack_voltage_warnings": "normal",
    "voltage_sensing_failure": "normal",
    "temp_sensing_failure": "normal",
    "current_sensing_failure": "normal",
    "power_switch_failure": "normal",
    "cell_voltage_difference_sensing_failure": "normal",
    "charging_switch_failure": "normal",
    "discharging_switch_failure": "normal",
    "current_limit_switch_failure": "normal",
    "cell_overvoltage": "normal",
    "cell_voltage_low": "normal",
    "pack_overvoltage": "normal",
    "pack_voltage_low": "normal",
    "charging_temp_high": "normal",
    "charging_temp_low": "normal",
    "discharging_temp_high": "normal",
    "discharging_temp_low": "normal",
    "ambient_temp_high": "normal",
    "component_temp_high": "normal",
    "charging_overcurrent": "normal",
    "discharging_overcurrent": "normal",
    "transient_overcurrent": "normal",
    "output_short_circuit": "normal",
    "transient_overcurrent_lock": "normal",
    "charging_high_voltage": "normal",
    "intermittent_power_supplement": "normal",
    "soc_low": "normal",
    "cell_low_voltage_forbidden_charging": "normal",
    "output_reverse_protection": "normal",
    "output_connection_failure": "normal",
    "discharge_switch": "on",
    "charge_switch": "on",
    "current_limit_switch": "off",
    "heating_limit_switch": "off",
    "equalization_cell_1": "off",
    "equalization_cell_2": "off",
    "equalization_cell_3": "off",
    "equalization_cell_4": "off",
    "equalization_cell_5": "off",
    "equalization_cell_6": "off",
    "equalization_cell_7": "off",
    "equalization_cell_8": "off",
    "equalization_cell_9": "off",
    "equalization_cell_10": "off",
    "equalization_cell_11": "off",
    "equalization_cell_12": "off",
    "equalization_cell_13": "off",
    "equalization_cell_14": "off",
    "equalization_cell_15": "off",
    "equalization_cell_16": "off",
    "discharge": "off",
    "charge": "off",
    "floating_charge": "off",
    "standby": "on",
    "power_off": "off",
    "disconnection_cell_1": "normal",
    "disconnection_cell_2": "normal",
    "disconnection_cell_3": "normal",
    "disconnection_cell_4": "normal",
    "disconnection_cell_5": "normal",
    "disconnection_cell_6": "normal",
    "disconnection_cell_7": "normal",
    "disconnection_cell_8": "normal",
    "disconnection_cell_9": "normal",
    "disconnection_cell_10": "normal",
    "disconnection_cell_11": "normal",
    "disconnection_cell_12": "normal",
    "disconnection_cell_13": "normal",
    "disconnection_cell_14": "normal",
    "disconnection_cell_15": "normal",
    "disconnection_cell_16": "normal",
    "auto_charging_wait": "normal",
    "manual_charging_wait": "normal",
    "eep_storage_failure": "normal",
    "rtc_clock_failure": "normal",
    "no_calibration_of_voltage": "normal",
    "no_calibration_of_current": "normal",
    "no_calibration_of_null_point": "normal"
}
```

## Configuring Home Assistant

Configure all sensor you'd like to use in Home Assistant as MQTT-Sensor.

- The provided `ha/create_ha_sensors.py` will create a yaml-file for each pack/all sensors for a given mqtt-topic and number of packs.
- Example: `python create_ha_sensors.py --mqtt_topic test/123 --number_of_packs 3` will create 6 yaml-files (3 telemetry and 3 telesignalization).
- The generated yaml is depended on a setting like `mqtt: !include_dir_merge_named mqtt` in `configuration.yaml`.
- If you are putting sensor directly int your `configuration.yaml`, add `platform: mqtt`, i.e. this

```
- name: Seplos Pack-0 Voltage Cell 1
  unique_id: seplos_pack_0_voltage_cell_1
  state_topic: seplos/pack-0/sensors
  value_template: '{{ value_json.telemetry.voltage_cell_1 }}'
  state_class: measurement
  unit_of_measurement: V
  suggested_display_precision: 3
  icon: mdi:battery
  device_class: voltage
```

becomes this

```
- platform: mqtt
  name: Seplos Pack-0 Voltage Cell 1
  unique_id: seplos_pack_0_voltage_cell_1
  state_topic: seplos/pack-0/sensors
  value_template: '{{ value_json.telemetry.voltage_cell_1 }}'
  state_class: measurement
  unit_of_measurement: V
  suggested_display_precision: 3
  icon: mdi:battery
  device_class: voltage
```
