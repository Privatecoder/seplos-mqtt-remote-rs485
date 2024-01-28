import yaml
import argparse

def main():
    parser = argparse.ArgumentParser(description='Generate MQTT sensor configurations for Home Assistant')

    # cli arguments
    parser.add_argument('--mqtt_topic', type=str, required=True, default="Seplos", help='MQTT topic name (string)')
    parser.add_argument('--number_of_packs', type=int, required=True, default=1, help='Number of pack-sensors to create (int)')

    # parse the arguments
    args = parser.parse_args()

    # use the arguments in the script
    mqtt_topic = args.mqtt_topic
    number_of_packs = args.number_of_packs

    # base sensor template
    base_sensor = {
        "name": "",
        "unique_id": "",
        "state_topic": "",
        "value_template": "",
        # 'unit_of_measurement', 'icon', and 'suggested_display_precision' are optional
    }

    # telemetry Sensors
    telemetry_sensor_templates = [
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

    # telesignalization Sensors
    telesignalization_sensor_templates = [
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
            "name": "Current Limit Switch",
            "value_template_key": "current_limit_switch",
            "icon": "mdi:alert-circle-outline",
            "entity_category": "diagnostic"
        },
        {
            "name": "Heating Limit Switch",
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

    def create_sensor(
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
        
        sensor = base_sensor.copy()

        # required keys
        sensor["name"] = f"Seplos Pack-{pack_no} {name}"
        sensor["unique_id"] = f"seplos_pack_{pack_no} {name}".replace(" ", "_").lower()
        sensor["state_topic"] = f"{mqtt_topic}/pack-{pack_no}/sensors"
        sensor["value_template"] = f"{{{{ value_json.{value_template_group}.{value_template_key} }}}}"

        # optional keys
        if state_class is not None:
            sensor["state_class"] = state_class
        if unit_of_measurement is not None:
            sensor["unit_of_measurement"] = unit_of_measurement
        if suggested_display_precision is not None:
            sensor["suggested_display_precision"] = suggested_display_precision
        if icon is not None:
            sensor["icon"] = icon
        if entity_category is not None:
            sensor["entity_category"] = entity_category
        if device_class is not None:
            sensor["device_class"] = device_class


        return sensor

    def create_similar_sensors(
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
        sensors = []
        for i in range(1, num_sensors + 1):
            name = f"{base_name} {i}"
            value_template_key = f"{base_value_template_key}_{i}"
            sensor = create_sensor(
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
            sensors.append(sensor)

        return sensors

    # Initialize an empty list for sensors
    telemetry_sensors = []
    telesignalization_sensors = []

    for pack_no in range(0, number_of_packs):
        # create multiple cell-voltage sensors
        cell_voltage_sensors = create_similar_sensors(
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
        telemetry_sensors = telemetry_sensors + cell_voltage_sensors

        # create multiple cells-temperature sensors
        temperature_sensors = create_similar_sensors(
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
        telemetry_sensors = telemetry_sensors + temperature_sensors

        # create all other sensors
        all_other_sensors = [create_sensor(pack_no=pack_no, value_template_group="telemetry", state_class="measurement", **config) for config in telemetry_sensor_templates]
        telemetry_sensors = telemetry_sensors + all_other_sensors

        # write yaml file for this pack
        filename = f"telemetry_sensors_pack-{pack_no}.yaml"
        with open(filename, "w") as file:
            file.write(f"## Begin Telemetry Sensors Seplos Pack-{pack_no}\n\n")
            yaml.dump(telemetry_sensors, file, indent=2, sort_keys=False)
            file.write(f"\n## End Telemetry Sensors Seplos Pack-{pack_no}")
        print(f"{filename} created successfully.")

    for pack_no in range(0, number_of_packs):
        # create multiple cell-voltage-warning sensors
        cell_voltage_warning_sensors = create_similar_sensors(
            num_sensors=16,
            pack_no=pack_no,
            value_template_group="telesignalization",
            base_value_template_key="voltage_warning_cell",
            base_name="Voltage Warning Cell",
            icon="mdi:alert-circle-outline",
            entity_category="diagnostic"
        )
        telesignalization_sensors = telesignalization_sensors + cell_voltage_warning_sensors

        # create multiple cell-disconnection sensors
        cell_disconnection_sensors = create_similar_sensors(
            num_sensors=16,
            pack_no=pack_no,
            value_template_group="telesignalization",
            base_value_template_key="disconnection_cell",
            base_name="Disconnection Cell",
            icon="mdi:alert-circle-outline",
            entity_category="diagnostic"
        )
        telesignalization_sensors = telesignalization_sensors + cell_disconnection_sensors

        # create multiple cell-equalization sensors
        cell_equalization_sensors = create_similar_sensors(
            num_sensors=16,
            pack_no=pack_no,
            value_template_group="telesignalization",
            base_value_template_key="equalization_cell",
            base_name="Equalization Cell",
            icon="mdi:alert-circle-outline",
            entity_category="diagnostic"
        )
        telesignalization_sensors = telesignalization_sensors + cell_equalization_sensors

        # create multiple cell-temperature-warning sensors
        cell_temperature_warning_sensors = create_similar_sensors(
            num_sensors=4,
            pack_no=pack_no,
            value_template_group="telesignalization",
            base_value_template_key="cell_temperature_warning",
            base_name="Cell Temperature Warning",
            icon="mdi:alert-circle-outline",
            entity_category="diagnostic"
        )
        telesignalization_sensors = telesignalization_sensors + cell_temperature_warning_sensors

        # create all other sensors
        all_other_sensors = [create_sensor(pack_no=pack_no, value_template_group="telesignalization", **config) for config in telesignalization_sensor_templates]
        telesignalization_sensors = telesignalization_sensors + all_other_sensors

        # write yaml file for this pack
        filename = f"telesignalization_sensors_pack-{pack_no}.yaml"
        with open(filename, "w") as file:
            file.write(f"## Begin Telesignalization Sensors Seplos Pack-{pack_no}\n\n")
            yaml.dump(telesignalization_sensors, file, indent=2, sort_keys=False)
            file.write(f"\n## End Telesignalization Sensors Seplos Pack-{pack_no}")
        print(f"{filename} created successfully.")

if __name__ == "__main__":
    main()