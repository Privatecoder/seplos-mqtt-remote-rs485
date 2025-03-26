# Seplos MQTT remote RS485
This is a python script that reads data from one or multiple (V2 / V16) Seplos battery packs (while using CAN to connect to your Inverter) via (a) (remote) RS485 connection(s) and publishes their stats to MQTT.

## Hardware requirements:

For **multiple packs** (only):

1. To connect multiple packs while using CAN to connect to your Inverter, you need to split the Master's CAN-port into **CAN+RS485**.
  
- The CAN-part of this port, i.e. pins 4+5 (CAN-H+CAN-L), connects to the inverter.
- The RS485-part, i.e. pins 6+7+8 (GND+RS485-A+RS485-B), connects to the **slave's CAN-port** (more specific: the RS485-part of it), i.e. pins 1+2+3 (GND+RS485-A+RS485-B) and is then **daisy chained** to all subsequent **slave's CAN-ports** (more specific: the RS485-part of them).
- **It is strictly necessary to make sure that the Master's RS485-part of the CAN-port does NOT have any connection to your inverter!**

For a **single pack** (only):

1. Connect your RS485 device directly to one of the two RS485-ports.

For all configurations:

2. (Remote) RS485 device ([Waveshare 2-CH RS485 to ETH has been tested](https://www.waveshare.com/2-ch-rs485-to-eth-b.htm))
3. Something that can run a Docker-Container
4. Seplos BMS [V2 / V16 has been tested](https://www.seplos.com/bms-2.0.html)
5. An MQTT broker

## Connecting the serial device to one or multiple battery packs:

When using one pack only, connect your Inverter to the CAN-port and your RS485 device directly to one of the two RS485-ports; no adapter/splitting/crimping involved.

For **multiple packs**, it is suggested to crimp your own cable(s) like so:

![seplos](https://github.com/user-attachments/assets/24b8224a-5c89-4057-9b51-27ef3bd31d92)

![waveshare-pins](https://github.com/Privatecoder/seplos-mqtt-remote-rs485/assets/45964815/34d5e8f3-43dd-46a6-8baf-5d9af662837d)

## Installation and configuration (Docker):

1. Configure and setup an MQTT broker with a user and password
2. Configure your (remote) RS485 device. For the Waveshare 2-CH RS485 to ETH this would most importantly be `IP Mode: Static` (must be a reachable IP within your network), `Port: 4196` (default), `Work Mode: TCP Server`, `Transfer Protocol: None`, `Baud Rate: 9600` (for Master with multiple Packs) **or** `Baud Rate: 19200` (for a single pack)
3. Modify the `config.ini` and edit its settings to your needs (**alternatively**: configure everything via ENV-vars)
4. Run the Docker Image, for example like this:

- For 1 master and 1 slave, i.e. two packs using ENV-vars:

```
docker run -itd \
  --restart unless-stopped \
  -e RS485_REMOTE_IP="192.168.1.200" \
  -e RS485_REMOTE_PORT="4196" \
  -e SERIAL_INTERFACE=/tmp/vcom0 \
  -e NUMBER_OF_PACKS=2 \
  -e MIN_CELL_VOLTAGE=2.500 \
  -e MAX_CELL_VOLTAGE=3.650 \
  -e MQTT_HOST=192.168.1.100 \
  -e MQTT_USERNAME=seplos-mqtt \
  -e MQTT_PASSWORD=my-secret-password \
  -e MQTT_TOPIC=seplos \
  -e MQTT_UPDATE_INTERVAL=1 \
  -e ENABLE_HA_DISCOVERY_CONFIG=true \
  -e HA_DISCOVERY_PREFIX=homeassistant \
  -e LOGGING_LEVEL=info \
  --name seplos-mqtt-rs485 \
  privatecoder/seplos-mqtt-remote-rs485:v3.0.0
```

- For 1 master and 1 slave, i.e. two packs using config.ini:

```
docker run -itd \
  --restart unless-stopped \
  -e RS485_REMOTE_IP="192.168.1.200" \
  -e RS485_REMOTE_PORT="4196" \
  -v $(pwd)/config-master.ini:/usr/src/app/config.ini \
  --name seplos-mqtt-rs485 \
  privatecoder/seplos-mqtt-remote-rs485:v3.0.0
```

- To run the script without socat / remote RS485 but local connections, don't set the `RS485_REMOTE_IP` and `RS485_REMOTE_PORT` ENV-vars, i.e:

```
docker run -itd \
  --restart unless-stopped \
  -e SERIAL_INTERFACE=/path/to/your/serialport \
  -e NUMBER_OF_PACKS=2 \
  -e MIN_CELL_VOLTAGE=2.500 \
  -e MAX_CELL_VOLTAGE=3.650 \
  -e MQTT_HOST=192.168.1.100 \
  -e MQTT_USERNAME=seplos-mqtt \
  -e MQTT_PASSWORD=my-secret-password \
  -e MQTT_TOPIC=seplos \
  -e MQTT_UPDATE_INTERVAL=1 \
  -e ENABLE_HA_DISCOVERY_CONFIG=true \
  -e HA_DISCOVERY_PREFIX=homeassistant \
  -e LOGGING_LEVEL=info \
  --name seplos-mqtt-rs485 \
  privatecoder/seplos-mqtt-remote-rs485:v3.0.0
```

**or**

```
docker run -itd \
  --restart unless-stopped \
  -v $(pwd)/config-master.ini:/usr/src/app/config.ini \
  --name seplos-mqtt-rs485 \
  privatecoder/seplos-mqtt-remote-rs485:v3.0.0
```

Available ENV-vars are:

- `RS485_REMOTE_IP` (IP of the remote RS485 device)
- `RS485_REMOTE_PORT` (Port of the remote RS485 device)

- `MQTT_HOST` (MQTT Broker IP, default: `192.168.1.100`)
- `MQTT_PORT` (MQTT Broker Port, default: `1883`)
- `MQTT_USERNAME` (MQTT Broker Username, default: `seplos-mqtt`)
- `MQTT_PASSWORD` (MQTT Broker Password, default: `my-secret-password`)
- `MQTT_TOPIC` (MQTT Broker Topic to publish to, default: `seplos`)
- `MQTT_UPDATE_INTERVAL` (Interval, in seconds, to update stats in MQTT after each circular reading is finished, 0 => continuous reading, default: `0`)

- `ENABLE_HA_DISCOVERY_CONFIG` (Enable Home Assistant config creation via MQTT for auto-discovery, default: `true`)
- `HA_DISCOVERY_PREFIX` (Home Assistant Topic to publish the config creations to, default: `homeassistant`)

- `NUMBER_OF_PACKS` (Fetch data of n packs, default: `1`)

- `MIN_CELL_VOLTAGE` (Min cell voltage as base calculation constant, as this cannot be read from the BMS, default: `2.500`)
- `MAX_CELL_VOLTAGE` (Max cell voltage as base calculation constant, as this cannot be read from the BMS, default: `3.650`)

- `SERIAL_INTERFACE` (Local RS485 device path, default: `/tmp/vcom0`)

- `LOGGING_LEVEL` (Logging level, available modes are info, error and debug, default: `info`)

Setting `RS485_REMOTE_IP` and `RS485_REMOTE_PORT` starts the docker image with socat, binding your remote RS485 device´s RS485 ports locally to `vcom0` (used by default in this script).
Not defining those will just start the script, however `SERIAL_INTERFACE` must match your existing serial-device – either passed to the container directly or using the privileged-flag (not recommended).

MQTT messages published by the script will look like this:
```
{
    "last_update": "2024-02-02 11:39:08",
    "telemetry": {
        "min_cell_voltage": 2.5,
        "max_cell_voltage": 3.65,
        "min_pack_voltage": 40.0,
        "max_pack_voltage": 58.4,
        "voltage_cell_1": 3.339,
        "voltage_cell_2": 3.34,
        "voltage_cell_3": 3.34,
        "voltage_cell_4": 3.34,
        "voltage_cell_5": 3.339,
        "voltage_cell_6": 3.342,
        "voltage_cell_7": 3.342,
        "voltage_cell_8": 3.34,
        "voltage_cell_9": 3.342,
        "voltage_cell_10": 3.343,
        "voltage_cell_11": 3.34,
        "voltage_cell_12": 3.341,
        "voltage_cell_13": 3.34,
        "voltage_cell_14": 3.346,
        "voltage_cell_15": 3.343,
        "voltage_cell_16": 3.342,
        "average_cell_voltage": 3.341,
        "lowest_cell": 1,
        "lowest_cell_voltage": 3.339,
        "highest_cell": 14,
        "highest_cell_voltage": 3.346,
        "delta_cell_voltage": 0.007,
        "cell_temperature_1": 11.5,
        "cell_temperature_2": 11.0,
        "cell_temperature_3": 10.9,
        "cell_temperature_4": 11.6,
        "ambient_temperature": 16.5,
        "components_temperature": 12.3,
        "dis_charge_current": 1.46,
        "total_pack_voltage": 53.46,
        "dis_charge_power": 78.052,
        "rated_capacity": 280.0,
        "battery_capacity": 280.0,
        "residual_capacity": 192.94,
        "soc": 68.9,
        "cycles": 7,
        "soh": 100.0,
        "port_voltage": 53.48
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
        "charge": "on",
        "floating_charge": "off",
        "standby": "off",
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

## Manual execution:

1. Clone the project
2. Make sure to have Python v3.10 or later installed
3. Edit `config.ini` in `src` to your needs (to connect your remote RS485 devices, bind them for example to `/tmp/vcom0` and `/tmp/vcom1` using socat like `socat pty,link=/tmp/vcom0,raw tcp:192.168.1.200:4196,retry,interval=.2,forever &` and `socat pty,link=/tmp/vcom1,raw tcp:192.168.1.201:4196,retry,interval=.2,forever &` or something similar)
4. Run the script, i.e. `python fetch_bms_data.py`

Its output will look like this (`LOGGING` `LEVEL` set to `info`):
```
INFO:SeplosBMS:Pack0:Requesting data...
INFO:SeplosBMS:Pack0:Telemetry Feedback: {
    "min_cell_voltage": 2.5,
    "max_cell_voltage": 3.65,
    "min_pack_voltage": 40.0,
    "max_pack_voltage": 58.4,
    "voltage_cell_1": 3.328,
    "voltage_cell_2": 3.328,
    "voltage_cell_3": 3.327,
    "voltage_cell_4": 3.328,
    "voltage_cell_5": 3.328,
    "voltage_cell_6": 3.328,
    "voltage_cell_7": 3.328,
    "voltage_cell_8": 3.329,
    "voltage_cell_9": 3.328,
    "voltage_cell_10": 3.329,
    "voltage_cell_11": 3.328,
    "voltage_cell_12": 3.328,
    "voltage_cell_13": 3.327,
    "voltage_cell_14": 3.327,
    "voltage_cell_15": 3.328,
    "voltage_cell_16": 3.328,
    "average_cell_voltage": 3.328,
    "lowest_cell": 3,
    "lowest_cell_voltage": 3.327,
    "highest_cell": 8,
    "highest_cell_voltage": 3.329,
    "delta_cell_voltage": 0.002,
    "cell_temperature_1": 13.0,
    "cell_temperature_2": 12.2,
    "cell_temperature_3": 12.1,
    "cell_temperature_4": 12.7,
    "ambient_temperature": 17.8,
    "components_temperature": 13.7,
    "dis_charge_current": 0.0,
    "total_pack_voltage": 53.25,
    "dis_charge_power": 0.0,
    "rated_capacity": 280.0,
    "battery_capacity": 280.0,
    "residual_capacity": 268.86,
    "soc": 96.0,
    "cycles": 7,
    "soh": 100.0,
    "port_voltage": 53.27
}
INFO:SeplosBMS:Pack0:Telesignalization feedback: {
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
INFO:SeplosBMS:Pack0:Sending updated stats to mqtt.
```

## Configuring Home Assistant

### Add Device(s):

- If `ENABLE_HA_DISCOVERY_CONFIG` is enabled, it triggers the publishing of auto discovery sensor configs in Home Assistant after a restart.
- Run the container and restart Home Assistant. The devices should be added automatically.

### Add Sensors to lovelace:

- The provided `lovelace.yaml` (in `ha-lovelace`) is using `card_mod`, `button-card`, `bar-card` and `apexcharts-card` (can be installed via HACS) and allows for a first start (value-based colors are based on [these number](https://docs.google.com/spreadsheets/d/1fkVZQvyQA_7x2OT59Ho25ul2QzdEgoV9M35y5uj6tsk/edit#gid=52730408)). `lovelace-plotly-graphs.yaml` is almost the same but uses `plotly-graph` instead of `apexcharts-card` for the graphs-section.

<img width="420" alt="image" src="https://github.com/Privatecoder/seplos-mqtt-remote-rs485/assets/45964815/df5b09e5-ed90-4026-b8b7-3294ff8ae0fb">
<img width="381" alt="image" src="https://github.com/Privatecoder/seplos-mqtt-remote-rs485/assets/45964815/2eff45a0-9a10-4fec-ba83-607b8941fbb6">

