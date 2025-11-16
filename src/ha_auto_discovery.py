"""
Handle creation and publishing of auto discovery configs for Home Assistant.
"""
import json
import logging
import copy
from typing import Optional, Dict, Any, List

logger = logging.getLogger("SeplosBMS.Discovery")

# Base sensor template
BASE_SENSOR = {
    "name": "",
    "uniq_id": "",  # unique_id
    "obj_id": "",  # object_id
    "stat_t": "",  # state_topic
    "val_tpl": "",  # value_template
    "avty": {},  # availability
    "dev": {}  # device
}

DEVICE_BASE_CONFIG = {
    "hw": "10C / 10E",  # hw_version
    "sw": "2.x / 16.x",  # sw_version
    "mdl": "BMS V14 / V16",  # model
    "mf": "Seplos"  # manufacturer
}

# Telemetry sensor templates
TELEMETRY_SENSOR_TEMPLATES: List[Dict[str, Any]] = [
    {
        "name": "Min Cell Voltage",
        "value_template_key": "min_cell_voltage",
        "device_class": "voltage",
        "unit_of_measurement": "V",
        "suggested_display_precision": 3,
        "icon": "mdi:cog"
    },
    {
        "name": "Max Cell Voltage",
        "value_template_key": "max_cell_voltage",
        "device_class": "voltage",
        "unit_of_measurement": "V",
        "suggested_display_precision": 3,
        "icon": "mdi:cog"
    },
    {
        "name": "Min Pack Voltage",
        "value_template_key": "min_pack_voltage",
        "device_class": "voltage",
        "unit_of_measurement": "V",
        "suggested_display_precision": 2,
        "icon": "mdi:cog"
    },
    {
        "name": "Max Pack Voltage",
        "value_template_key": "max_pack_voltage",
        "device_class": "voltage",
        "unit_of_measurement": "V",
        "suggested_display_precision": 2,
        "icon": "mdi:cog"
    },
    {
        "name": "Average Cell Voltage",
        "value_template_key": "average_cell_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 3,
        "icon": "mdi:chart-line"
    },
    {
        "name": "Lowest Cell",
        "value_template_key": "lowest_cell",
        "icon": "mdi:numeric"
    },
    {
        "name": "Lowest Cell Voltage",
        "value_template_key": "lowest_cell_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 3,
        "icon": "mdi:arrow-down-thin"
    },
    {
        "name": "Highest Cell",
        "value_template_key": "highest_cell",
        "icon": "mdi:numeric"
    },
    {
        "name": "Highest Cell Voltage",
        "value_template_key": "highest_cell_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 3,
        "icon": "mdi:arrow-up-thin"
    },
    {
        "name": "Delta Cell Voltage",
        "value_template_key": "delta_cell_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 3,
        "icon": "mdi:delta"
    },
    {
        "name": "Delta Cell Temperature",
        "value_template_key": "delta_cell_temperature",
        "device_class": "temperature_delta",
        "state_class": "measurement",
        "unit_of_measurement": "°C",
        "suggested_display_precision": 1,
        "icon": "mdi:delta"
    },
    {
        "name": "Ambient Temperature",
        "value_template_key": "ambient_temperature",
        "device_class": "temperature",
        "state_class": "measurement",
        "unit_of_measurement": "°C",
        "suggested_display_precision": 1,
        "icon": "mdi:thermometer"
    },
    {
        "name": "Components Temperature",
        "value_template_key": "components_temperature",
        "device_class": "temperature",
        "state_class": "measurement",
        "unit_of_measurement": "°C",
        "suggested_display_precision": 1,
        "icon": "mdi:thermometer"
    },
    {
        "name": "Dis-/Charge Current",
        "value_template_key": "dis_charge_current",
        "device_class": "current",
        "state_class": "measurement",
        "unit_of_measurement": "A",
        "suggested_display_precision": 2,
        "icon": "mdi:current-dc"
    },
    {
        "name": "Dis-/Charge Power",
        "value_template_key": "dis_charge_power",
        "device_class": "power",
        "state_class": "measurement",
        "unit_of_measurement": "W",
        "suggested_display_precision": 2,
        "icon": "mdi:flash"
    },
    {
        "name": "Total Pack Voltage",
        "value_template_key": "total_pack_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
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
        "state_class": "measurement",
        "suggested_display_precision": 2,
        "icon": "mdi:battery"
    },
    {
        "name": "Residual Capacity",
        "value_template_key": "residual_capacity",
        "state_class": "measurement",
        "unit_of_measurement": "Ah",
        "suggested_display_precision": 2,
        "icon": "mdi:battery-50"
    },
    {
        "name": "State of Charge",
        "value_template_key": "state_of_charge",
        "device_class": "battery",
        "state_class": "measurement",
        "unit_of_measurement": "%",
        "suggested_display_precision": 1,
        "icon": "mdi:battery"
    },
    {
        "name": "Charging Cycles",
        "value_template_key": "charging_cycles",
        "unit_of_measurement": "cycles",
        "state_class": "total_increasing",
        "icon": "mdi:counter"
    },
    {
        "name": "State of Health",
        "value_template_key": "state_of_health",
        "state_class": "measurement",
        "unit_of_measurement": "%",
        "suggested_display_precision": 1,
        "icon": "mdi:battery-heart"
    },
    {
        "name": "Port Voltage",
        "value_template_key": "port_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 2,
        "icon": "mdi:flash-triangle"
    },
    {
        "name": "Last Update",
        "value_template_key": "last_update",
        "icon": "mdi:update"
    }
]

# Telesignalization sensor templates
TELESIGNALIZATION_SENSOR_TEMPLATES: List[Dict[str, Any]] = [
    ## Info data sensors

    # Individual cell voltage warnings via create_similar_sensor_config

    {
        "name": "Alarm Cell Voltage",
        "value_template_key": "any_cell_voltage_alarm",
        "icon": "mdi:flash-alert"
    },

    # Individual cell temperature warnings via create_similar_sensor_config

    {
        "name": "Alarm Cell Temperature",
        "value_template_key": "any_cell_temperature_alarm",
        "icon": "mdi:thermometer-alert"
    },
    {
        "name": "Alarm Ambient Temp.",
        "value_template_key": "ambient_temperature_alarm",
        "icon": "mdi:thermometer-alert"
    },
    {
        "name": "Alarm Component Temp.",
        "value_template_key": "component_temperature_alarm",
        "icon": "mdi:thermometer-alert"
    },
    {
        "name": "Alarm Dis-/Charge Current",
        "value_template_key": "dis_charging_current_alarm",
        "icon": "mdi:flash-alert"
    },
    {
        "name": "Alarm Pack Voltage",
        "value_template_key": "pack_voltage_alarm",
        "icon": "mdi:flash-alert"
    },
    {
        "name": "System Status",
        "value_template_key": "system_status",
        "icon": "mdi:information-outline"
    },

    ## Diagnostic data sensors

    # Warning 2
    {
        "name": "Cell Overvoltage",
        "value_template_key": "cell_overvoltage",
        "icon": "mdi:flash-alert",
        "entity_category": "diagnostic"
    },
    {
        "name": "Cell Voltage Low",
        "value_template_key": "cell_voltage_low",
        "icon": "mdi:flash-alert",
        "entity_category": "diagnostic"
    },

    {
        "name": "Pack Overvoltage",
        "value_template_key": "pack_overvoltage",
        "icon": "mdi:flash-alert",
        "entity_category": "diagnostic"
    },
    {
        "name": "Pack Voltage Low",
        "value_template_key": "pack_voltage_low",
        "icon": "mdi:flash-alert",
        "entity_category": "diagnostic"
    },

    # Warning 3
    {
        "name": "Charging Temp. High",
        "value_template_key": "charging_temperature_high",
        "icon": "mdi:thermometer-alert",
        "entity_category": "diagnostic"
    },
    {
        "name": "Charging Temp. Low",
        "value_template_key": "charging_temperature_low",
        "icon": "mdi:snowflake-alert",
        "entity_category": "diagnostic"
    },
    {
        "name": "Discharging Temp. High",
        "value_template_key": "discharging_temperature_high",
        "icon": "mdi:thermometer-alert",
        "entity_category": "diagnostic"
    },
    {
        "name": "Discharging Temp. Low",
        "value_template_key": "discharging_temperature_low",
        "icon": "mdi:snowflake-alert",
        "entity_category": "diagnostic"
    },

    # Warning 4
    {
        "name": "Ambient Temp. High",
        "value_template_key": "ambient_temperature_high",
        "icon": "mdi:thermometer-alert",
        "entity_category": "diagnostic"
    },
    {
        "name": "Ambient Temp. Low",
        "value_template_key": "ambient_temperature_low",
        "icon": "mdi:snowflake-alert",
        "entity_category": "diagnostic"
    },
    {
        "name": "Component Temp. High",
        "value_template_key": "component_temperature_high",
        "icon": "mdi:thermometer-alert",
        "entity_category": "diagnostic"
    },

    # Warning 5
    {
        "name": "Charging Overcurrent",
        "value_template_key": "charging_overcurrent",
        "icon": "mdi:flash-alert",
        "entity_category": "diagnostic"
    },
    {
        "name": "Discharging Overcurrent",
        "value_template_key": "discharging_overcurrent",
        "icon": "mdi:flash-alert",
        "entity_category": "diagnostic"
    },
    {
        "name": "Transient Overcurrent",
        "value_template_key": "transient_overcurrent",
        "icon": "mdi:flash-alert",
        "entity_category": "diagnostic"
    },
    {
        "name": "Output Short Circuit",
        "value_template_key": "output_short_circuit",
        "icon": "mdi:flash-alert",
        "entity_category": "diagnostic"
    },

    # Warning 6
    {
        "name": "SoC Low",
        "value_template_key": "soc_low",
        "icon": "mdi:battery-alert-variant-outline",
        "entity_category": "diagnostic"
    }
]

TELESIGNALIZATION_BINARY_SENSOR_TEMPLATES: List[Dict[str, Any]] = [
    ## Warning group sensors

    # Warning 1
    {
        "name": "Voltage Sensing Failure",
        "value_template_key": "voltage_sensing_failure",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Fault",
        "payload_off": "OK"
    },
    {
        "name": "Temp. Sensing Failure",
        "value_template_key": "temperature_sensing_failure",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Fault",
        "payload_off": "OK"
    },
    {
        "name": "Current Sensing Failure",
        "value_template_key": "current_sensing_failure",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Fault",
        "payload_off": "OK"
    },
    {
        "name": "Power Switch Failure",
        "value_template_key": "power_switch_failure",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Fault",
        "payload_off": "OK"
    },
    {
        "name": "Cell Voltage Difference Sensing Failure",
        "value_template_key": "cell_voltage_difference_sensing_failure",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Fault",
        "payload_off": "OK"
    },
    {
        "name": "Charging Switch Failure",
        "value_template_key": "charging_switch_failure",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Fault",
        "payload_off": "OK"
    },
    {
        "name": "Discharging Switch Failure",
        "value_template_key": "discharging_switch_failure",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Fault",
        "payload_off": "OK"
    },
    {
        "name": "Current Limit Switch Failure",
        "value_template_key": "current_limit_switch_failure",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Fault",
        "payload_off": "OK"
    },

    # Warning 4
    {
        "name": "Low Temp. Heating",
        "value_template_key": "low_temperature_heating",
        "entity_category": "diagnostic",
        "device_class": "problem"
    },

    # Warning 6
    {
        "name": "Charging High Voltage Protection",
        "value_template_key": "charging_high_voltage_protection",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Protection",
        "payload_off": "OK"
    },
    {
        "name": "Intermittent Power Supplement",
        "value_template_key": "intermittent_power_supplement",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Warning",
        "payload_off": "OK"
    },
    {
        "name": "Cell Low Volt. Forb. Charg.",
        "value_template_key": "cell_low_voltage_forbidden_charging",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Protection",
        "payload_off": "OK"
    },
    {
        "name": "Output Reverse Polarity Protection",
        "value_template_key": "output_reverse_polarity_protection",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Protection",
        "payload_off": "OK"
    },
    {
        "name": "Output Connection Failure",
        "value_template_key": "output_connection_failure",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Fault",
        "payload_off": "OK"
    },

    # Warning 7
    {
        "name": "Auto Charging Wait",
        "value_template_key": "auto_charging_wait",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Warning",
        "payload_off": "OK"
    },
    {
        "name": "Manual Charging Wait",
        "value_template_key": "manual_charging_wait",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Warning",
        "payload_off": "OK"
    },

    # Warning 8
    {
        "name": "EEP Storage Failure",
        "value_template_key": "eep_storage_failure",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Fault",
        "payload_off": "OK"
    },
    {
        "name": "RTC Clock Failure",
        "value_template_key": "rtc_clock_failure",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Fault",
        "payload_off": "OK"
    },
    {
        "name": "No Calibration Of Voltage",
        "value_template_key": "no_calibration_of_voltage",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Warning",
        "payload_off": "OK"
    },
    {
        "name": "No Calibration Of Current",
        "value_template_key": "no_calibration_of_current",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Warning",
        "payload_off": "OK"
    },
    {
        "name": "No Calibration Of Null Point",
        "value_template_key": "no_calibration_of_null_point",
        "entity_category": "diagnostic",
        "device_class": "problem",
        "payload_on": "Warning",
        "payload_off": "OK"
    },

    # Switch status
    {
        "name": "Discharge Switch",
        "value_template_key": "discharge_switch",
        "entity_category": "diagnostic",
        "device_class": "power"
    },
    {
        "name": "Charge Switch",
        "value_template_key": "charge_switch",
        "entity_category": "diagnostic",
        "device_class": "power"
    },
    {
        "name": "Current Limit Switch",
        "value_template_key": "current_limit_switch",
        "entity_category": "diagnostic",
        "device_class": "power"
    },
    {
        "name": "Heating Switch",
        "value_template_key": "heating_switch",
        "entity_category": "diagnostic",
        "device_class": "power"
    },

    # Balancer status via create_similar_sensor_config

    # Disconnection status via create_similar_sensor_config
]


class AutoDiscoveryConfig:
    """Handle Home Assistant auto-discovery configuration creation and publishing."""

    def __init__(self, mqtt_topic: str, discovery_prefix: str, mqtt_client) -> None:
        """
        Initialize AutoDiscoveryConfig.

        Args:
            mqtt_topic: MQTT topic where sensor data gets published
            discovery_prefix: Discovery prefix for Home Assistant (defaults to 'homeassistant')
            mqtt_client: MQTT client instance for publishing
        """
        self.mqtt_topic = mqtt_topic
        self.discovery_prefix = discovery_prefix
        self.mqtt_client = mqtt_client
        self._device_info_published = set()

    # -------------------------------------------------------------------------
    # Interne Hilfsfunktionen zur Vereinheitlichung
    # -------------------------------------------------------------------------

    def _add_device_info(self, entity: Dict[str, Any], pack_no: int) -> None:
        """Setze passende device-Infos für das gegebene Pack."""
        if pack_no not in self._device_info_published:
            entity["dev"] = {**DEVICE_BASE_CONFIG}
            entity["dev"]["name"] = f"Seplos BMS Pack-{pack_no} ({'Master' if pack_no == 0 else 'Slave'})"
            entity["dev"]["ids"] = f"seplos_bms_pack_{pack_no}"
            if pack_no > 0:
                entity["dev"]["via_device"] = "seplos_bms_pack_0"
            self._device_info_published.add(pack_no)
        else:
            entity["dev"] = {"ids": f"seplos_bms_pack_{pack_no}"}
            if pack_no > 0:
                entity["dev"]["via_device"] = "seplos_bms_pack_0"

    def _build_base_entity(
        self,
        pack_no: int,
        name: str,
        value_template: str,
        uniq_obj_id: str,
    ) -> Dict[str, Any]:
        """Erzeuge Grundstruktur eines Sensors/Binary Sensors basierend auf BASE_SENSOR."""
        entity = copy.deepcopy(BASE_SENSOR)

        # Device-Infos
        self._add_device_info(entity, pack_no)

        # Required fields
        entity["name"] = name
        entity["avty"]["t"] = f"{self.mqtt_topic}/availability"
        entity["stat_t"] = f"{self.mqtt_topic}/pack-{pack_no}/sensors"
        entity["val_tpl"] = value_template
        entity["uniq_id"] = uniq_obj_id
        entity["obj_id"] = uniq_obj_id

        return entity

    def _apply_optional_fields(self, entity: Dict[str, Any], optional_fields: Dict[str, Any]) -> None:
        """Füge optionale Felder hinzu, wenn sie nicht None sind."""
        for key, value in optional_fields.items():
            if value is not None:
                entity[key] = value

    def _publish_config(
        self,
        entity_type: str,
        pack_no: int,
        name: str,
        value_template_key: str,
        config: Dict[str, Any],
    ) -> None:
        """Generische Publish-Funktion für Sensoren und Binary-Sensoren."""
        discovery_topic = f"{self.discovery_prefix}/{entity_type}/seplos-mqtt-pack-{pack_no}/{value_template_key}/config"

        try:
            self.mqtt_client.publish(
                discovery_topic,
                json.dumps(config),
                retain=True,
                qos=1
            )
            logger.debug(f"Published discovery config for pack {pack_no}, {entity_type}: {name}")
        except Exception as e:
            logger.error(f"Failed to publish discovery config: {e}")

    # -------------------------------------------------------------------------
    # Build-Funktionen
    # -------------------------------------------------------------------------

    def _build_binary_sensor_config(
        self,
        pack_no: int,
        name: str,
        value_template_group: str,
        value_template_key: str,
        icon: Optional[str] = None,
        entity_category: Optional[str] = None,
        device_class: Optional[str] = None,
        payload_on: Optional[str] = None,
        payload_off: Optional[str] = None,
        options: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Build binary sensor configuration dictionary.
        """
        value_template = f"{{{{ value_json.{value_template_group}.binary.{value_template_key} }}}}"
        binary_sensor = self._build_base_entity(
            pack_no=pack_no,
            name=name,
            value_template=value_template,
            uniq_obj_id = f"seplos_bms_pack_{pack_no}_{value_template_key}",
        )

        optional_fields = {
            "ic": icon,
            "ent_cat": entity_category,
            "dev_cla": device_class,
            "pl_on": payload_on,
            "pl_off": payload_off,
            "ops": options
        }
        self._apply_optional_fields(binary_sensor, optional_fields)

        return binary_sensor

    def _build_sensor_config(
        self,
        pack_no: int,
        name: str,
        value_template_group: str,
        value_template_key: str,
        unit_of_measurement: Optional[str] = None,
        suggested_display_precision: Optional[int] = None,
        icon: Optional[str] = None,
        device_class: Optional[str] = None,
        state_class: Optional[str] = None,
        entity_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build sensor configuration dictionary.
        """
        sensor = self._build_base_entity(
            pack_no=pack_no,
            name=name,
            value_template=f"{{{{ value_json.{value_template_group}.normal.{value_template_key} }}}}",
            uniq_obj_id=f"seplos_bms_pack_{pack_no}_{value_template_key}",
        )

        optional_fields = {
            "stat_cla": state_class,
            "unit_of_meas": unit_of_measurement,
            "sug_dsp_prc": suggested_display_precision,
            "ic": icon,
            "ent_cat": entity_category,
            "dev_cla": device_class
        }
        self._apply_optional_fields(sensor, optional_fields)

        return sensor

    # -------------------------------------------------------------------------
    # Publish-Funktionen (API unverändert)
    # -------------------------------------------------------------------------

    def _publish_binary_sensor_config(
        self,
        pack_no: int,
        binary_sensor_name: str,
        value_template_key: str,
        binary_sensor_config: Dict[str, Any]
    ) -> None:
        """
        Publish binary sensor configuration to MQTT.
        """
        self._publish_config(
            entity_type="binary_sensor",
            pack_no=pack_no,
            name=binary_sensor_name,
            value_template_key=value_template_key,
            config=binary_sensor_config,
        )

    def _publish_sensor_config(
        self,
        pack_no: int,
        sensor_name: str,
        value_template_key: str,
        sensor_config: Dict[str, Any]
    ) -> None:
        """
        Publish sensor configuration to MQTT.
        """
        self._publish_config(
            entity_type="sensor",
            pack_no=pack_no,
            name=sensor_name,
            value_template_key=value_template_key,
            config=sensor_config,
        )

    # -------------------------------------------------------------------------
    # Öffentliche Erzeugungs-Funktionen
    # -------------------------------------------------------------------------

    def create_binary_sensor_config(
        self,
        pack_no: int,
        name: str,
        value_template_group: str,
        value_template_key: str,
        icon: Optional[str] = None,
        device_class: Optional[str] = None,
        entity_category: Optional[str] = None,
        payload_on: Optional[str] = None,
        payload_off: Optional[str] = None,
        options: Optional[List[str]] = None
    ) -> None:
        """
        Create and publish unique binary sensor configuration.
        """

        logger.debug(f"Creating auto-discovery binary sensors for pack {pack_no}")

        binary_sensor_config = self._build_binary_sensor_config(
            pack_no=pack_no,
            value_template_group=value_template_group,
            name=name,
            value_template_key=value_template_key,
            icon=icon,
            device_class=device_class,
            entity_category=entity_category,
            payload_on=payload_on,
            payload_off=payload_off,
            options=options
        )

        self._publish_binary_sensor_config(pack_no, name, value_template_key, binary_sensor_config)

        logger.debug(f"Auto-discovery binary sensors published for pack {pack_no}")

    def create_sensor_config(
        self,
        pack_no: int,
        value_template_group: str,
        name: str,
        value_template_key: str,
        unit_of_measurement: Optional[str] = None,
        suggested_display_precision: Optional[int] = None,
        icon: Optional[str] = None,
        device_class: Optional[str] = None,
        state_class: Optional[str] = None,
        entity_category: Optional[str] = None
    ) -> None:
        """
        Create and publish unique sensor configuration.
        """

        logger.debug(f"Creating auto-discovery sensors for pack {pack_no}")

        sensor_config = self._build_sensor_config(
            pack_no=pack_no,
            value_template_group=value_template_group,
            name=name,
            value_template_key=value_template_key,
            unit_of_measurement=unit_of_measurement,
            suggested_display_precision=suggested_display_precision,
            icon=icon,
            device_class=device_class,
            state_class=state_class,
            entity_category=entity_category
        )

        self._publish_sensor_config(pack_no, name, value_template_key, sensor_config)

        logger.debug(f"Auto-discovery sensors published for pack {pack_no}")

    def create_similar_binary_sensor_config(
        self,
        num_sensors: int,
        pack_no: int,
        value_template_group: str,
        base_value_template_key: str,
        base_name: str,
        entity_category: Optional[str] = None,
        device_class: Optional[str] = None,
        icon: Optional[str] = None,
        payload_on: Optional[str] = None,
        payload_off: Optional[str] = None,
        options: Optional[List[str]] = None
    ) -> None:
        """
        Create multiple similar binary sensor configurations.
        """
        for i in range(1, num_sensors + 1):
            name = f"{base_name} {i}"
            value_template_key = f"{base_value_template_key}_{i}"

            self.create_binary_sensor_config(
                pack_no=pack_no,
                name=name,
                value_template_group=value_template_group,
                value_template_key=value_template_key,
                entity_category=entity_category,
                device_class=device_class,
                icon=icon,
                payload_on=payload_on,
                payload_off=payload_off,
                options=options
            )

    def create_similar_sensor_config(
        self,
        num_sensors: int,
        pack_no: int,
        value_template_group: str,
        base_value_template_key: str,
        base_name: str,
        entity_category: Optional[str] = None,
        device_class: Optional[str] = None,
        state_class: Optional[str] = None,
        unit_of_measurement: Optional[str] = None,
        suggested_display_precision: Optional[int] = None,
        icon: Optional[str] = None
    ) -> None:
        """
        Create multiple similar sensor configurations.
        """
        for i in range(1, num_sensors + 1):
            name = f"{base_name} {i}"
            value_template_key = f"{base_value_template_key}_{i}"

            self.create_sensor_config(
                pack_no=pack_no,
                name=name,
                value_template_group=value_template_group,
                value_template_key=value_template_key,
                entity_category=entity_category,
                device_class=device_class,
                state_class=state_class,
                unit_of_measurement=unit_of_measurement,
                suggested_display_precision=suggested_display_precision,
                icon=icon
            )

    def create_autodiscovery_sensors(self, pack_no: int) -> None:
        """
        Create all Home Assistant auto-discovery sensors for a pack.

        Args:
            pack_no: Pack number to create sensors for
        """
        # Clear device info flag for this pack to ensure it's included in first sensor
        self._device_info_published.discard(pack_no)

        ## Telemetry sensors

        # Create cell voltage sensors
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
            icon="mdi:battery-outline"
        )

        # Create cell temperature sensors
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

        # Create telemetry sensors
        for config in TELEMETRY_SENSOR_TEMPLATES:
            self.create_sensor_config(
                pack_no=pack_no,
                value_template_group="telemetry",
                **config
            )

        ## Telesignalization sensors

        # Create Cell voltage warning sensors
        self.create_similar_sensor_config(
            num_sensors=16,
            pack_no=pack_no,
            value_template_group="telesignalization",
            base_value_template_key="cell_voltage_alarm",
            base_name="Voltage Alarm Cell",
            icon="mdi:flash-alert",
            entity_category="diagnostic"
        )

        # Create Cell Temperature warning sensors
        self.create_similar_sensor_config(
            num_sensors=4,
            pack_no=pack_no,
            value_template_group="telesignalization",
            base_value_template_key="cell_temperature_alarm",
            base_name="Cell Temperature Alarm",
            icon="mdi:thermometer-alert",
            entity_category="diagnostic"
        )

        # Create Balancer sensors
        self.create_similar_binary_sensor_config(
            num_sensors=16,
            pack_no=pack_no,
            value_template_group="telesignalization",
            base_value_template_key="balancer_cell",
            base_name="Balancer Cell",
            entity_category="diagnostic",
            device_class="running"
        )

        # Create Disconnection sensors
        self.create_similar_binary_sensor_config(
            num_sensors=16,
            pack_no=pack_no,
            value_template_group="telesignalization",
            base_value_template_key="disconnection_cell",
            base_name="Connection Cell",
            entity_category="diagnostic",
            device_class="connectivity",
            payload_on="OK",
            payload_off="Warning"
        )

        # Create telesignalization sensors
        for config in TELESIGNALIZATION_SENSOR_TEMPLATES:
            self.create_sensor_config(
                pack_no=pack_no,
                value_template_group="telesignalization",
                **config
            )

        # Create telesignalization binary sensors
        for config in TELESIGNALIZATION_BINARY_SENSOR_TEMPLATES:
            self.create_binary_sensor_config(
                pack_no=pack_no,
                value_template_group="telesignalization",
                **config
            )
