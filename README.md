# Seplos MQTT remote RS485
This is a python script that reads data from one or multiple Seplos (while using CAN to connect to your Inverter) battery packs via a (remote) RS485 connection and publish their stats to MQTT.

## Hardware requirements:

1. (Remote) RS485 device [Waveshare 2-CH RS485 to ETH has been tested](https://www.waveshare.com/2-ch-rs485-to-eth-b.htm)
2. For multiple packs while using CAN to connect to your Inverter, you need a splitter ([this splitter works for me](https://www.amazon.de/gp/product/B00D3KIQXC)) to split the CAN port into CAN+RS485 and two separate RS485 connections (the Waveshare 2-CH RS485 to ETH has two RS485 ports)
3. Something that can run a Docker-Container
4. Seplos BMS [V2 / V16 has been tested](https://www.seplos.com/bms-2.0.html)
5. An MQTT broker

## Connecting serial devices to multiple battery packs

![293281298-295d06a6-5b9f-47a3-82e7-0cbc17bbaf2e-2](https://github.com/Privatecoder/seplos-mqtt-remote-rs485/assets/45964815/bbf51f50-a898-4c64-b8b5-93811509b02e)

## Installation and configuration

1. Configure and setup an MQTT broker with a user and password
2. Configure your remote RS485 device, for the Waveshare 2-CH RS485 to ETH this would most importantly be `IP Mode: Static` (must be a reachable IP within your network), `Port: 4196` (default), `Work Mode: TCP Server`, `Transfer Protocol: None`, `Baud Rate: 9600` (for Master with multiple Packs) ** or** `Baud Rate: 19200` (for Slaves)
3. Modify the `config.ini` and edit its settings to your needs
4. Run the Docker Image, for example like this:

For the master pack: `docker run -itd -e RS485_REMOTE_IP="192.168.1.200" -e RS485_REMOTE_PORT="4196" -v $(pwd)/config-master.ini:/usr/src/app/config.ini --name seplos-mqtt-master privatecoder/seplos-mqtt-remote-rs485:v1.0.0
`
For the slaves: `docker run -itd -e RS485_REMOTE_IP="192.168.1.201" -e RS485_REMOTE_PORT="4196" -v $(pwd)/config-slaves.ini:/usr/src/app/config.ini --name seplos-mqtt-slaves privatecoder/seplos-mqtt-remote-rs485:v1.0.0`

MQTT messages will look like this:
```
{
    "status": {
        "cell_0_voltage": 3.01,
        "cell_1_voltage": 3.02,
        "cell_2_voltage": 3.008,
        "cell_3_voltage": 3.012,
        "cell_4_voltage": 2.995,
        "cell_5_voltage": 3.024,
        "cell_6_voltage": 3.038,
        "cell_7_voltage": 3.018,
        "cell_8_voltage": 3.018,
        "cell_9_voltage": 3.045,
        "cell_10_voltage": 3.002,
        "cell_11_voltage": 3.045,
        "cell_12_voltage": 3.015,
        "cell_13_voltage": 3.075,
        "cell_14_voltage": 3.054,
        "cell_15_voltage": 3.018,
        "lowest_cell": 4,
        "highest_cell": 13,
        "cell_temp_0": 7.7,
        "cell_temp_1": 7.2,
        "cell_temp_2": 7.1,
        "cell_temp_3": 7.7,
        "env_temp": 12.5,
        "pwr_temp": 8.7,
        "current": 0.0,
        "voltage": 48.4,
        "capacity_rated": 280.0,
        "capacity": 280.0,
        "capacity_remain": 100.28,
        "soc": 35.8,
        "cycles": 6
    },
    "alarm": {
        "voltage_cell_low": 1,
        "voltage_cell_high": 0,
        "voltage_low": 0,
        "voltage_high": 0,
        "temp_low_charge": 0,
        "temp_high_charge": 0,
        "temp_low_discharge": 0,
        "temp_high_discharge": 0,
        "current_over": 0,
        "current_under": 0,
        "soc_low": 0,
        "discharge_fet_enabled": true,
        "charge_fet_enabled": true
    }
}
```

## Manual execution

1. Clone the project
2. Edit `config.ini` in `src` to your needs (to connect your remote RS485 device, bind it for example to `/tmp/vcom0` using socat like `socat pty,link=/tmp/vcom0,raw tcp:192.168.1.200:4196,retry,interval=.2,forever` or something similar)
3. Run the script, i.e. `python fetch_bms_data.py`

Its output will look like this (`LOGGING` `LEVEL` set to `info`):
```
INFO:SeplosBMS:Battery-Pack 0 stats:
INFO:SeplosBMS:Voltage Cell[0]=2.999V
INFO:SeplosBMS:Voltage Cell[1]=3.016V
INFO:SeplosBMS:Voltage Cell[2]=3.027V
INFO:SeplosBMS:Voltage Cell[3]=3.071V
INFO:SeplosBMS:Voltage Cell[4]=3.023V
INFO:SeplosBMS:Voltage Cell[5]=3.048V
INFO:SeplosBMS:Voltage Cell[6]=3.038V
INFO:SeplosBMS:Voltage Cell[7]=3.039V
INFO:SeplosBMS:Voltage Cell[8]=3.059V
INFO:SeplosBMS:Voltage Cell[9]=3.041V
INFO:SeplosBMS:Voltage Cell[10]=3.008V
INFO:SeplosBMS:Voltage Cell[11]=3.027V
INFO:SeplosBMS:Voltage Cell[12]=3.023V
INFO:SeplosBMS:Voltage Cell[13]=3.008V
INFO:SeplosBMS:Voltage Cell[14]=2.986V
INFO:SeplosBMS:Voltage Cell[15]=3.03V
INFO:SeplosBMS:Lowest Cell[14]
INFO:SeplosBMS:Highest Cell[3]
INFO:SeplosBMS:Temp Cell[0]=8.3°C
INFO:SeplosBMS:Temp Cell[1]=7.7°C
INFO:SeplosBMS:Temp Cell[2]=7.6°C
INFO:SeplosBMS:Temp Cell[3]=8.4°C
INFO:SeplosBMS:Current = -0.49A
INFO:SeplosBMS:Voltage = 48.44V
INFO:SeplosBMS:Rated Capacity = 280.0Ah
INFO:SeplosBMS:Capacity = 280.0Ah
INFO:SeplosBMS:Remaining Capacity = 60.85Ah
INFO:SeplosBMS:SOC = 21.7%
INFO:SeplosBMS:Cycles = 6
INFO:SeplosBMS:Environment temp = 12.4°C
INFO:SeplosBMS:Power temp = 8.9°C
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
