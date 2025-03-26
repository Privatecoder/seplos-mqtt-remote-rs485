"""
handle creation and publishing of auto discovery configs for home assistant
"""
import json

# base sensor template
BASE_SENSOR = {
  "name": "",
  # unique_id
  "uniq_id": "",
  # object_id
  "obj_id": "",
  # state_topic
  "stat_t": "",
  # value_template
  "val_tpl": "",
  # availability
  "avty": {},
  # device
  "dev": {}
}

DEVICE_BASE_CONFIG = {
  # hw_version
  "hw": "10C / 10E",
  # sw_version
  "sw": "2.x / 16.x",
  # model
  "mdl": "BMS V14 / V16",
  # manufacturer
  "mf": "Seplos"
}

# telemetry sensor
TELEMETRY_SENSOR_TEMPLATES = [
  {
    "name": "Min Pack Voltage",
    "value_template_key": "min_pack_voltage",
    "device_class": "voltage",
    "unit_of_measurement": "V",
    "suggested_display_precision": 2,
    "icon": "mdi:server"
  },
  {
    "name": "Max Pack Voltage",
    "value_template_key": "max_pack_voltage",
    "device_class": "voltage",
    "unit_of_measurement": "V",
    "suggested_display_precision": 2,
    "icon": "mdi:server"
  },
  {
    "name": "Min Cell Voltage",
    "value_template_key": "min_cell_voltage",
    "device_class": "voltage",
    "unit_of_measurement": "V",
    "suggested_display_precision": 3,
    "icon": "mdi:battery"
  },
  {
    "name": "Max Cell Voltage",
    "value_template_key": "max_cell_voltage",
    "device_class": "voltage",
    "unit_of_measurement": "V",
    "suggested_display_precision": 3,
    "icon": "mdi:battery"
  },
  {
    "name": "Average Cell Voltage",
    "value_template_key": "average_cell_voltage",
    "device_class": "voltage",
    "unit_of_measurement": "V",
    "suggested_display_precision": 3,
    "icon": "mdi:battery"
  },
  {
    "name": "Lowest Cell",
    "value_template_key": "lowest_cell",
    "icon": "mdi:battery-minus-outline"
  },
  {
    "name": "Lowest Cell Voltage",
    "value_template_key": "lowest_cell_voltage",
    "device_class": "voltage",
    "unit_of_measurement": "V",
    "suggested_display_precision": 3,
    "icon": "mdi:battery-minus-outline"
  },
  {
    "name": "Highest Cell",
    "value_template_key": "highest_cell",
    "icon": "mdi:battery-plus-outline"
  },
  {
    "name": "Highest Cell Voltage",
    "value_template_key": "highest_cell_voltage",
    "device_class": "voltage",
    "unit_of_measurement": "V",
    "suggested_display_precision": 3,
    "icon": "mdi:battery-plus-outline"
  },
  {
    "name": "Delta Cell Voltage",
    "value_template_key": "delta_cell_voltage",
    "device_class": "voltage",
    "unit_of_measurement": "V",
    "suggested_display_precision": 3,
    "icon": "mdi:delta"
  },
  {
    "name": "Ambient Temperature",
    "value_template_key": "ambient_temperature",
    "device_class": "temperature",
    "unit_of_measurement": "°C",
    "suggested_display_precision": 1,
    "icon": "mdi:thermometer"
  },
  {
    "name": "Components Temperature",
    "value_template_key": "components_temperature",
    "device_class": "temperature",
    "unit_of_measurement": "°C",
    "suggested_display_precision": 1,
    "icon": "mdi:thermometer"
  },
  {
    "name": "Dis-/Charge Current",
    "value_template_key": "dis_charge_current",
    "device_class": "current",
    "unit_of_measurement": "A",
    "suggested_display_precision": 2,
    "icon": "mdi:current-dc"
  },
  {
    "name": "Dis-/Charge Power",
    "value_template_key": "dis_charge_power",
    "device_class": "power",
    "unit_of_measurement": "W",
    "suggested_display_precision": 2,
    "icon": "mdi:battery"
  },
  {
    "name": "Total Pack Voltage",
    "value_template_key": "total_pack_voltage",
    "device_class": "voltage",
    "unit_of_measurement": "V",
    "suggested_display_precision": 2,
    "icon": "mdi:server"
  },
  {
    "name": "Rated Capacity",
    "value_template_key": "rated_capacity",
    "unit_of_measurement": "Ah",
    "suggested_display_precision": 2,
    "icon": "mdi:battery"
  },
  {
    "name": "Battery Capacity",
    "value_template_key": "battery_capacity",
    "unit_of_measurement": "Ah",
    "suggested_display_precision": 2,
    "icon": "mdi:battery-50"
  },
  {
    "name": "Residual Capacity",
    "value_template_key": "residual_capacity",
    "unit_of_measurement": "Ah",
    "suggested_display_precision": 2,
    "icon": "mdi:battery-50"
  },
  {
    "name": "State of Charge",
    "value_template_key": "soc",
    "device_class": "battery",
    "unit_of_measurement": "%",
    "suggested_display_precision": 1,
    "icon": "mdi:battery-50"
  },
  {
    "name": "Charging Cycles",
    "value_template_key": "cycles",
    "icon": "mdi:battery-sync"
  },
  {
    "name": "State of Health",
    "value_template_key": "soh",
    "unit_of_measurement": "%",
    "suggested_display_precision": 1,
    "icon": "mdi:heart-flash"
  },
  {
    "name": "Port Voltage",
    "value_template_key": "port_voltage",
    "device_class": "voltage",
    "unit_of_measurement": "V",
    "suggested_display_precision": 2,
    "icon": "mdi:battery"
  }
]

# telesignalization sensor
TELESIGNALIZATION_SENSOR_TEMPLATES = [
  {
    "name": "Ambient Temperature Warning",
    "value_template_key": "ambient_temperature_warning",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Component Temperature Warning",
    "value_template_key": "component_temperature_warning",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Dis-/Charging Current Warning",
    "value_template_key": "dis_charging_current_warning",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Pack Voltage Warning",
    "value_template_key": "pack_voltage_warning",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Voltage Sensing Failure",
    "value_template_key": "voltage_sensing_failure",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Temp Sensing Failure",
    "value_template_key": "temp_sensing_failure",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Current Sensing Failure",
    "value_template_key": "current_sensing_failure",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Power Switch Failure",
    "value_template_key": "power_switch_failure",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Cell Voltage Difference Sensing Failure",
    "value_template_key": "cell_voltage_difference_sensing_failure",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Charging Switch Failure",
    "value_template_key": "charging_switch_failure",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Discharging Switch Failure",
    "value_template_key": "discharging_switch_failure",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Current Limit Switch Failure",
    "value_template_key": "current_limit_switch_failure",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Cell Overvoltage",
    "value_template_key": "cell_overvoltage",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Cell Voltage Low",
    "value_template_key": "cell_voltage_low",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Pack Overvoltage",
    "value_template_key": "pack_overvoltage",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Pack Voltage Low",
    "value_template_key": "pack_voltage_low",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Charging Temp High",
    "value_template_key": "charging_temp_high",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Charging Temp Low",
    "value_template_key": "charging_temp_low",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Discharging Temp High",
    "value_template_key": "discharging_temp_high",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Discharging Temp Low",
    "value_template_key": "discharging_temp_low",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Ambient Temp High",
    "value_template_key": "ambient_temp_high",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Component Temp High",
    "value_template_key": "component_temp_high",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Charging Overcurrent",
    "value_template_key": "charging_overcurrent",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Discharging Overcurrent",
    "value_template_key": "discharging_overcurrent",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Transient Overcurrent",
    "value_template_key": "transient_overcurrent",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Output Short Circuit",
    "value_template_key": "output_short_circuit",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Transient Overcurrent Lock",
    "value_template_key": "transient_overcurrent_lock",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Charging High Voltage",
    "value_template_key": "charging_high_voltage",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Intermittent Power Supplement",
    "value_template_key": "intermittent_power_supplement",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Soc Low",
    "value_template_key": "soc_low",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Cell Low Voltage Forbidden Charging",
    "value_template_key": "cell_low_voltage_forbidden_charging",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Output Reverse Protection",
    "value_template_key": "output_reverse_protection",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Output Connection Failure",
    "value_template_key": "output_connection_failure",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Discharge Switch",
    "value_template_key": "discharge_switch",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Charge Switch",
    "value_template_key": "charge_switch",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Current Limit Active",
    "value_template_key": "current_limit_switch",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Heating Limit Active",
    "value_template_key": "heating_limit_switch",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Discharge",
    "value_template_key": "discharge",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Charge",
    "value_template_key": "charge",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Floating Charge",
    "value_template_key": "floating_charge",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Standby",
    "value_template_key": "standby",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Power Off",
    "value_template_key": "power_off",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Auto Charging Wait",
    "value_template_key": "auto_charging_wait",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Manual Charging Wait",
    "value_template_key": "manual_charging_wait",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Eep Storage Failure",
    "value_template_key": "eep_storage_failure",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "Rtc Clock Failure",
    "value_template_key": "rtc_clock_failure",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "No Calibration Of Voltage",
    "value_template_key": "no_calibration_of_voltage",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "No Calibration Of Current",
    "value_template_key": "no_calibration_of_current",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  },
  {
    "name": "No Calibration Of Null Point",
    "value_template_key": "no_calibration_of_null_point",
    "icon": "mdi:alert-circle-outline",
    "entity_category": "diagnostic"
  }
]

class AutoDiscoveryConfig():
    """
    this class holds all methods for creating Home Assitant auto-discovery config
    """
    def __init__(self, mqtt_topic, discovery_prefix, mqtt_client):

        # sensor data gets published to this mqtt topic
        self.mqtt_topic = mqtt_topic

        # sensor config data gets published here, defaults to homeassistant
        self.discovery_prefix = discovery_prefix

        # mqtt client
        self.mqtt_client = mqtt_client

        # flag to indicate wheater this is the first sensor config created
        self.first_run: bool = True

    def create_sensor_config(
        self,
        pack_no,
        value_template_group,
        name,
        value_template_key,
        unit_of_measurement=None,
        suggested_display_precision=None,
        icon=None,
        device_class=None,
        state_class=None,
        entity_category=None
      ):
        """
        Create unique sensor config
        """
        # copy base keys from BASE_SENSOR
        sensor = BASE_SENSOR.copy()

        # device details only on first sensor (reduce payload length)
        if self.first_run is True:
            # device
            sensor["dev"] = {**DEVICE_BASE_CONFIG}
            # device name
            sensor["dev"]["name"] = f"Seplos BMS Pack-{pack_no} ({'Master' if pack_no == 0 else 'Slave'})"
            self.first_run = False

        # name
        sensor["name"] = name
        # availability topic
        sensor["avty"]["t"] = f"{self.mqtt_topic}/availability"
        # state_topic
        sensor["stat_t"] = f"{self.mqtt_topic}/pack-{pack_no}/sensors"
        # value_template
        sensor["val_tpl"] = f"{{{{ value_json.{value_template_group}.{value_template_key} }}}}"
        # unique_id
        sensor["uniq_id"] = f"seplos_bms_pack_{pack_no}_{name}".replace(" ", "_").lower()
        # object_id
        sensor["obj_id"] = f"seplos_bms_pack_{pack_no}_{name}".replace(" ", "_").lower()
        # device identifiers
        sensor["dev"]["ids"] = f"seplos_bms_pack_{pack_no}"

        # optional keys
        if state_class is not None:
            # state_class
            sensor["stat_cla"] = state_class
        if unit_of_measurement is not None:
            # unit_of_measurement
            sensor["unit_of_meas"] = unit_of_measurement
        if suggested_display_precision is not None:
            # suggested_display_precision
            sensor["sug_dsp_prc"] = suggested_display_precision
        if icon is not None:
            # icon
            sensor["ic"] = icon
        if entity_category is not None:
            # entity_category
            sensor["ent_cat"] = entity_category
        if device_class is not None:
            # device_class
            sensor["dev_cla"] = device_class

        # publish sensor (<discovery_prefix>/<component>/[<node_id>/]<object_id>/config)
        self.mqtt_client.publish(
            f"{self.discovery_prefix}/sensor/seplos-mqtt-pack-{pack_no}/{value_template_key}/config",
            json.dumps(sensor, indent=4),
            retain=False
        )

    def create_similar_sensor_config(
          self,
          num_sensors,
          pack_no,
          value_template_group,
          base_value_template_key,
          base_name,
          entity_category=None,
          device_class=None,
          state_class=None,
          unit_of_measurement=None,
          suggested_display_precision=None,
          icon=None
      ):
        """
        Run create_sensor_config for given number of similar sensors
        """
        # create name and value_template for each similar sensor and create through create_sensor_config
        for i in range(1, num_sensors + 1):
            name = f"{base_name} {i}"
            value_template_key = f"{base_value_template_key}_{i}"
            self.create_sensor_config(
              # required keys
              pack_no=pack_no,
              name=name,
              value_template_group=value_template_group,
              value_template_key=value_template_key,

              # optional keys
              entity_category=entity_category if entity_category is not None else None,
              device_class=device_class if device_class is not None else None,
              state_class=state_class if state_class is not None else None,
              unit_of_measurement=unit_of_measurement if unit_of_measurement is not None else None,
              suggested_display_precision=suggested_display_precision if suggested_display_precision is not None else None,
              icon=icon if icon is not None else None,
            )

    def create_autodiscovery_sensors(self, pack_no: int) -> None:
        """
        Create HomeAssistant auto discovery sensors
        """
        # reset first_run for every function call
        self.first_run = True

        # create multiple cell-voltage sensors
        self.create_similar_sensor_config(
            num_sensors=16,
            pack_no=pack_no,
            value_template_group="telemetry",
            base_value_template_key="voltage_cell",
            base_name="Voltage Cell",
            device_class="voltage",
            state_class="measurement",
            unit_of_measurement="V",
            suggested_display_precision=3,
            icon="mdi:battery"
        )

        # create multiple cells-temperature sensors
        self.create_similar_sensor_config(
            num_sensors=4,
            pack_no=pack_no,
            value_template_group="telemetry",
            base_value_template_key="cell_temperature",
            base_name="Cell Temperature",
            device_class="temperature",
            state_class="measurement",
            unit_of_measurement="°C",
            suggested_display_precision=1,
            icon="mdi:thermometer"
        )

        # create all other sensors
        for config in TELEMETRY_SENSOR_TEMPLATES:
            self.create_sensor_config(
                pack_no=pack_no,
                value_template_group="telemetry",
                state_class="measurement",
                **config
            )

        # create multiple cell-voltage-warning sensors
        self.create_similar_sensor_config(
            num_sensors=16,
            pack_no=pack_no,
            value_template_group="telesignalization",
            base_value_template_key="voltage_warning_cell",
            base_name="Voltage Warning Cell",
            icon="mdi:alert-circle-outline",
            entity_category="diagnostic"
        )

        # create multiple cell-disconnection sensors
        self.create_similar_sensor_config(
            num_sensors=16,
            pack_no=pack_no,
            value_template_group="telesignalization",
            base_value_template_key="disconnection_cell",
            base_name="Disconnection Cell",
            icon="mdi:alert-circle-outline",
            entity_category="diagnostic"
        )

        # create multiple cell-equalization sensors
        self.create_similar_sensor_config(
            num_sensors=16,
            pack_no=pack_no,
            value_template_group="telesignalization",
            base_value_template_key="equalization_cell",
            base_name="Equalization Cell",
            icon="mdi:alert-circle-outline",
            entity_category="diagnostic"
        )

        # create multiple cell-temperature-warning sensors
        self.create_similar_sensor_config(
            num_sensors=4,
            pack_no=pack_no,
            value_template_group="telesignalization",
            base_value_template_key="cell_temperature_warning",
            base_name="Cell Temperature Warning",
            icon="mdi:alert-circle-outline",
            entity_category="diagnostic"
        )

        # create all other sensors
        for config in TELESIGNALIZATION_SENSOR_TEMPLATES:
            self.create_sensor_config(
                pack_no=pack_no,
                value_template_group="telesignalization",
                **config
            )
