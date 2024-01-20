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
2. Configure your (remote) RS485 device, for the Waveshare 2-CH RS485 to ETH this would most importantly be `IP Mode: Static` (must be a reachable IP within your network), `Port: 4196` (default), `Work Mode: TCP Server`, `Transfer Protocol: None`, `Baud Rate: 9600` (for Master with multiple Packs) ** or** `Baud Rate: 19200` (for Slaves)
3. Modify the `config.ini` and edit its settings to your needs
4. Run the Docker Image, for example like this:

- For the master pack: `docker run -itd -e RS485_REMOTE_IP="192.168.1.200" -e RS485_REMOTE_PORT="4196" -v $(pwd)/config-master.ini:/usr/src/app/config.ini --name seplos-mqtt-master privatecoder/seplos-mqtt-remote-rs485:v1.0.0`

- For the slaves: `docker run -itd -e RS485_REMOTE_IP="192.168.1.201" -e RS485_REMOTE_PORT="4196" -v $(pwd)/config-slaves.ini:/usr/src/app/config.ini --name seplos-mqtt-slaves privatecoder/seplos-mqtt-remote-rs485:v1.0.0`

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
    "status": {
        "min_pack_voltage": 46.4,
        "max_pack_voltage": 55.2,
        "cell_1_voltage": 3.239,
        "cell_2_voltage": 3.238,
        "cell_3_voltage": 3.241,
        "cell_4_voltage": 3.24,
        "cell_5_voltage": 3.24,
        "cell_6_voltage": 3.238,
        "cell_7_voltage": 3.242,
        "cell_8_voltage": 3.243,
        "cell_9_voltage": 3.24,
        "cell_10_voltage": 3.242,
        "cell_11_voltage": 3.241,
        "cell_12_voltage": 3.238,
        "cell_13_voltage": 3.241,
        "cell_14_voltage": 3.244,
        "cell_15_voltage": 3.241,
        "cell_16_voltage": 3.239,
        "average_cell_voltage": 3.24,
        "lowest_cell": 2,
        "lowest_cell_voltage": 3.238,
        "highest_cell": 14,
        "highest_cell_voltage": 3.244,
        "delta_cell_voltage": 0.006,
        "cells_temp_1": 8.1,
        "cells_temp_2": 7.2,
        "cells_temp_3": 7.2,
        "cells_temp_4": 7.8,
        "env_temp": 13.2,
        "mosfet_temp": 8.9,
        "current": 2.96,
        "voltage": 51.85,
        "power": 153.476,
        "capacity_rated": 280.0,
        "capacity": 280.0,
        "capacity_remain": 18.99,
        "soc": 6.7,
        "cycles": 6,
        "soh": 100.0,
        "port_voltage": 51.88
    },
    "alarm": {
        "voltage_cell_low": 0,
        "voltage_cell_high": 0,
        "voltage_low": 0,
        "voltage_high": 0,
        "temp_low_charge": 0,
        "temp_high_charge": 0,
        "temp_low_discharge": 0,
        "temp_high_discharge": 0,
        "current_over": 0,
        "current_under": 0,
        "soc_low": 1,
        "discharge_mosfet_enabled": true,
        "charge_mosfet_enabled": true
    }
}
```

## Manual execution

1. Clone the project
2. Make sure to have Python v3.10 or later installed
3. Edit `config.ini` in `src` to your needs (to connect your remote RS485 device, bind it for example to `/tmp/vcom0` using socat like `socat pty,link=/tmp/vcom0,raw tcp:192.168.1.200:4196,retry,interval=.2,forever` or something similar)
4. Run the script, i.e. `python fetch_bms_data.py`

Its output will look like this (`LOGGING` `LEVEL` set to `info`):
```
INFO:SeplosBMS:Voltage Cell[1] = 3.243V
INFO:SeplosBMS:Voltage Cell[2] = 3.24V
INFO:SeplosBMS:Voltage Cell[3] = 3.241V
INFO:SeplosBMS:Voltage Cell[4] = 3.241V
INFO:SeplosBMS:Voltage Cell[5] = 3.242V
INFO:SeplosBMS:Voltage Cell[6] = 3.239V
INFO:SeplosBMS:Voltage Cell[7] = 3.239V
INFO:SeplosBMS:Voltage Cell[8] = 3.24V
INFO:SeplosBMS:Voltage Cell[9] = 3.243V
INFO:SeplosBMS:Voltage Cell[10] = 3.242V
INFO:SeplosBMS:Voltage Cell[11] = 3.242V
INFO:SeplosBMS:Voltage Cell[12] = 3.245V
INFO:SeplosBMS:Voltage Cell[13] = 3.242V
INFO:SeplosBMS:Voltage Cell[14] = 3.244V
INFO:SeplosBMS:Voltage Cell[15] = 3.242V
INFO:SeplosBMS:Voltage Cell[16] = 3.245V
INFO:SeplosBMS:Average Cell Voltage = 3.242V
INFO:SeplosBMS:Lowest Cell = [6]
INFO:SeplosBMS:Lowest Cell Voltage = 3.239V
INFO:SeplosBMS:Highest Cell = [12]
INFO:SeplosBMS:Highest Cell Voltage = 3.239V
INFO:SeplosBMS:Delta Cell Voltage = 0.006V
INFO:SeplosBMS:Voltage = 51.87V
INFO:SeplosBMS:Min Pack Voltage = 46.4V
INFO:SeplosBMS:Max Pack Voltage = 55.2V
INFO:SeplosBMS:Current = 3.29A
INFO:SeplosBMS:Power = 170.652W
INFO:SeplosBMS:Port Voltage = 51.87V
INFO:SeplosBMS:Rated Capacity = 280.0Ah
INFO:SeplosBMS:Capacity = 280.0Ah
INFO:SeplosBMS:Remaining Capacity = 19.85Ah
INFO:SeplosBMS:SOC = 7.0%
INFO:SeplosBMS:SOH = 100.0%
INFO:SeplosBMS:Cycles = 7
INFO:SeplosBMS:Environment Temp = 10.6°C
INFO:SeplosBMS:Mosfet Temp = 6.7°C
INFO:SeplosBMS:Cells Temp 1 = 5.8°C
INFO:SeplosBMS:Cells Temp 2 = 5.1°C
INFO:SeplosBMS:Cells Temp 3 = 5.1°C
INFO:SeplosBMS:Cells Temp 4 = 5.8°C
INFO:SeplosBMS:Battery-Pack 4 alarm status:
INFO:SeplosBMS:Alarm Voltage Cell low = 0
INFO:SeplosBMS:Alarm Voltage Cell high = 0
INFO:SeplosBMS:Alarm Voltage low = 0
INFO:SeplosBMS:Alarm Voltage high = 0
INFO:SeplosBMS:Alarm Temp low charge = 0
INFO:SeplosBMS:Alarm Temp high charge = 0
INFO:SeplosBMS:Alarm Temp low discharge = 0
INFO:SeplosBMS:Alarm Temp high discharge = 0
INFO:SeplosBMS:Alarm Current over = 0
INFO:SeplosBMS:Alarm Current under = 0
INFO:SeplosBMS:Alarm SoC low = 1
INFO:SeplosBMS:Discharge MOSFET enabled = True
INFO:SeplosBMS:Discharge MOSFET enabled = True
```

## Configuring Home Assistant

Configure all sensor you'd like to use in Home Assistant as MQTT-Sensor.

- The provided `ha/seplos_pack-1.yaml` might be helpful
- The provided sample yaml is depended on a setting like `mqtt: !include_dir_merge_named mqtt` in `configuration.yaml`.
- If you are putting sensor directly int your `configuration.yaml`, add `platform: mqtt`, i.e. this

```
  - name: "Seplos Pack-1 Cell 0 Voltage"
    state_topic: "seplos/pack-1/sensors"
    unit_of_measurement: 'V'
    value_template: "{{ value_json.status.cell_0_voltage }}"
    unique_id: "seplos_pack_1_cell_0_voltage"
```

becomes this

```
  - platform: mqtt
    name: "Seplos Pack-1 Cell 0 Voltage"
    state_topic: "seplos/pack-1/sensors"
    unit_of_measurement: 'V'
    value_template: "{{ value_json.status.cell_0_voltage }}"
    unique_id: "seplos_pack_1_cell_0_voltage"
```
