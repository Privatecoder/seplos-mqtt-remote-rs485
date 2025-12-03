# Seplos MQTT remote RS485

This is a python script that runs in a container (standalone execution is possible) and reads data from one or multiple V2 / V16 Seplos BMS (also called 10C and 10E) via a remote or local RS485 connection and publishes its/their stats to MQTT.

Home Assistant Sensor auto discovery can be enabled (optional)

**NOTE: There is now also a [Home Assistant Add-on version](https://github.com/Privatecoder/seplos-mqtt-rs485-add-on). This project will continue to be maintained in parallel for all those who do not use Home Assistant or who want to use and analyze the data elsewhere.**

## Hardware requirements

- A remote or local RS485 device ([the Waveshare 2-CH RS485 to ETH gateway has been tested](https://www.waveshare.com/2-ch-rs485-to-eth-b.htm))
- **For MULTIPLE packs**: A self-crimped cable with multiple plugs or two or more splitters ([this one works for me](https://www.amazon.de/gp/product/B00D3KIQXC) – one of which always needs to be modified (more information [below](https://github.com/Privatecoder/seplos-mqtt-rs485-add-on#wiring-the-rs485-device-to-multiple-battery-packs))
- **For a SINGLE pack**: A regular patch-cable from one of the two RS485-ports of the pack to the terminals of your RS485 device
- One or multiple [Seplos BMS V2 / V16](https://www.seplos.com/bms-2.0.html)
- A configured and running MQTT broker

## Wiring the RS485 device to MULTIPLE battery packs

Carefully check the provided wiring scheme [below](https://github.com/Privatecoder/seplos-mqtt-rs485-add-on/edit/main/README.md#wiring-sample) (the PINK lines). There are two ways to approach the same result:
1. A single, self-crimped cable with multiple plugs, crimped as shown in the picture below (recommended).
2. Two or more splitters, one of which need to be modified (easier if you don't like crimping) – if you have two packs, you need two splitters, three packs require three splitters and so on.

When using splitters, the **first** splitter (the one that connects to the Master's CAN-port) needs to be modified like so:
- On one of the two outlets cut all but the three pins of the RS485-part (check the PINK lines in the [image below](https://github.com/Privatecoder/seplos-mqtt-rs485-add-on/edit/main/README.md#wiring-sample))
- On the other outlet cut all but the two pins of the CAN-part (check the PINK lines in the [image below](https://github.com/Privatecoder/seplos-mqtt-rs485-add-on/edit/main/README.md#wiring-sample))

Example for four packs:

- Connect the first, **modified** splitter to the **CAN-Port (NOT one of the RS485!) of the Master**
  - The outlet with only the two CAN-pins connect to your inverter using a regular patch-cable.
  - The outlet with only the three RS485-pins connect to the first slave using a regular patch-cable.
- Connect the second, **unmodified** splitter to the **CAN-Port (NOT one of the RS485!) of the first Slave**
  - Use one outlet to connect the regular patch-cable, coming from the Master
  - Use the other outlet to connect a regular patch-cable to the second Slave
- Connect the third, **unmodified** splitter to the **CAN-Port (NOT one of the RS485!) of the second Slave**
  - Use one outlet to connect the regular patch-cable, coming from the first Slave
  - Use the other outlet to connect a regular patch-cable to the third Slave
- Connect the fourth, **unmodified** splitter to the **CAN-Port (NOT one of the RS485!) of the third Slave**
  - Use one outlet to connect the regular patch-cable, coming from the second Slave
  - Use the other outlet to connect a regular patch-cable to your RS485-device (the one that is used to read the data, i.e. the Waveshare 2-CH RS485 to ETH gateway or similar)

### Wiring sample:

<img alt="wiring sample" src="https://github.com/user-attachments/assets/dc72fa68-df39-41e8-8033-4776d622d618" width="500">

### Seplos pin assignment (CAN-port)

- `1/8` => `RS485-B`
- `2/7` => `RS485-A`
- `4` => `CAN-H`
- `5` => `CAN-L`
- `3/6` => `GND`

<img width="400" alt="seplos pin assignment" src="https://github.com/user-attachments/assets/af477cbd-9cba-422f-9e0f-880e4e17fc45" />

### Waveshare pin assignment (RS485-port)

- `orange` => `RS485-A`
- `orange-white` => `RS485-B`
- `green-white` => `GND`

<img alt="waveshare gateway pinout" src="https://github.com/user-attachments/assets/442e0fee-5ec7-495b-81d7-013c56f1f304" width="100">

## Wiring the RS485 device to ONE SINGLE battery pack

When using a regular patch-cable, cut one of its connectors and take the `orange`, `orange-white` and `green-white` wires to crimp a terminal onto each of them. Then connect it to the waveshare device like so:

- `orange` => `RS485-A`
- `orange-white` => `RS485-B`
- `green-white` => `PE`

<img alt="waveshare gateway pinout" src="https://github.com/user-attachments/assets/442e0fee-5ec7-495b-81d7-013c56f1f304" width="100">

## Installation and configuration

1. Configure and setup an MQTT broker with a user and password
2. Configure your RS485 device. For the Waveshare 2-CH RS485 to ETH gateway this would most importantly be `IP Mode: Static` (must be a reachable IP within your network), `Port: 4196` (default), `Work Mode: TCP Server`, `Transfer Protocol: None`, `Baud Rate: 9600` (for **MULTIPLE** packs) **or** `Baud Rate: 19200` (for a **SINGLE** pack).
3. Configure and setup something that can run a container (when using the container-image) or python script (when just using the script)
4. Set the required ENV-vars
5. Run the Docker Image, for example like this:

- For 1 master and 1 slave, i.e. two packs using ENV-vars:

```bash
docker run -itd \
  --restart unless-stopped \
  -e RS485_REMOTE_IP="192.168.1.200" \
  -e RS485_REMOTE_PORT="4196" \
  -e SERIAL_INTERFACE=/tmp/vcom0 \
  -e NUMBER_OF_PACKS=2 \
  -e MIN_CELL_VOLTAGE=2.500 \
  -e MAX_CELL_VOLTAGE=3.650 \
  -e MQTT_HOST=192.168.1.100 \
  -e MQTT_PORT=1883 \
  -e MQTT_USERNAME=seplos-mqtt \
  -e MQTT_PASSWORD=my-secret-password \
  -e MQTT_TOPIC=seplos \
  -e MQTT_UPDATE_INTERVAL=1 \
  -e ENABLE_HA_DISCOVERY_CONFIG=true \
  -e INVERT_HA_DIS_CHARGE_MEASUREMENTS=true \
  -e HA_DISCOVERY_PREFIX=homeassistant \
  -e LOGGING_LEVEL=info \
  --name seplos-mqtt-rs485 \
  ghcr.io/privatecoder/seplos-mqtt-remote-rs485:v4.0.2
```

- To run the script without socat / remote RS485 but local connections, don't set the `RS485_REMOTE_IP` and `RS485_REMOTE_PORT` ENV-vars, i.e:

```bash
docker run -itd \
  --restart unless-stopped \
  -e SERIAL_INTERFACE=/path/to/your/serialport \
  -e NUMBER_OF_PACKS=2 \
  -e MIN_CELL_VOLTAGE=2.500 \
  -e MAX_CELL_VOLTAGE=3.650 \
  -e MQTT_HOST=192.168.1.100 \
  -e MQTT_PORT=1883 \
  -e MQTT_USERNAME=seplos-mqtt \
  -e MQTT_PASSWORD=my-secret-password \
  -e MQTT_TOPIC=seplos \
  -e MQTT_UPDATE_INTERVAL=1 \
  -e ENABLE_HA_DISCOVERY_CONFIG=true \
  -e INVERT_HA_DIS_CHARGE_MEASUREMENTS=true \
  -e HA_DISCOVERY_PREFIX=homeassistant \
  -e LOGGING_LEVEL=info \
  --name seplos-mqtt-rs485 \
  ghcr.io/privatecoder/seplos-mqtt-remote-rs485:v4.0.2
```

Available ENV-vars are:

- `RS485_REMOTE_IP` (IP of the remote RS485 device)
- `RS485_REMOTE_PORT` (Port of the remote RS485 device)

- `MQTT_HOST` (MQTT Broker IP, default: `192.168.1.100`)
- `MQTT_PORT` (MQTT Broker Port, default: `1883`)
- `MQTT_USERNAME` (MQTT Broker Username, default: `seplos-mqtt`)
- `MQTT_PASSWORD` (MQTT Broker Password, default: `my-secret-password`)
- `MQTT_TOPIC` (MQTT Broker Topic to publish to, default: `seplos`)
- `MQTT_UPDATE_INTERVAL` (Time to wait (in seconds) in between each circular reading to update stats in MQTT, `0` => continuous reading, default: `0`)

- `ENABLE_HA_DISCOVERY_CONFIG` (Enable Home Assistant sensor config creation via MQTT for auto-discovery, default: `true`)
- `INVERT_HA_DIS_CHARGE_MEASUREMENTS` (Inverts the values of the charging and discharging sensors in Home Assistant, default: `false`)
- `HA_DISCOVERY_PREFIX` (Home Assistant Topic to publish the config creations to, default: `homeassistant`)

- `NUMBER_OF_PACKS` (Fetch data of n packs, default: `1`)

- `MIN_CELL_VOLTAGE` (Min cell voltage as base calculation constant, as this cannot be read from the BMS, default: `2.500`)
- `MAX_CELL_VOLTAGE` (Max cell voltage as base calculation constant, as this cannot be read from the BMS, default: `3.650`)

- `SERIAL_INTERFACE` (Local RS485 device path, default: `/tmp/vcom0`)

- `LOGGING_LEVEL` (Logging level, available modes are `info`, `error` and `debug`, default: `info`)

Setting `RS485_REMOTE_IP` and `RS485_REMOTE_PORT` starts the docker image with socat, binding your remote RS485 device´s RS485 ports locally to `vcom0` (used by default in this script).

Not defining those will just start the script, however `SERIAL_INTERFACE` must match your existing serial-device – either passed to the container directly or using the privileged-flag (not recommended).

```text

```

## Manual execution

1. Clone the project
2. Make sure to have Python v3.10 or later installed
3. Set ENV-vars to your needs
4. Run the script, i.e. `python3 fetch_bms_data.py`

## Configuring Home Assistant

### Add Device(s)

- If `ENABLE_HA_DISCOVERY_CONFIG` is set to `TRUE`, it triggers the publishing of auto discovery sensor configs in Home Assistant. The devices should be added automatically.

### Add Sensors to lovelace

- The provided `ha-lovelace/lovelace.yaml` is using custom add-ons like `mushroom-template-card`, `entity-progress-card`, `expander-card`, `button-card`, `bar-card`, `card_mod` and `browser_mod` (can be installed via HACS) and allows for a first start (value-based colors are based on EVE LF280K datasheets and measurements and personal preferences).

<img width="400" alt="lovelace sample multiple packs card" src="https://github.com/user-attachments/assets/814f7540-57a1-40db-9ac1-5d1a3e9a19a3" />
<img width="400" alt="lovelace sample pack info" src="https://github.com/user-attachments/assets/829acb11-d50c-43a0-b818-96fbe28907aa" />
<img width="400" alt="lovelace sample pack errors and warnings" src="https://github.com/user-attachments/assets/419ed442-98ec-4985-98a6-6b4f5b4b9841" />
