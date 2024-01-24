#!/bin/bash

# This script concatenates YAML files starting with 'telemetry' into a single file.

# Define the output file
combined_telemetry="combined_telemetry.yaml"
combined_telesignalization="combined_telesignalization.yaml"

# Check if the output file already exists
if [ -f "$combined_telemetry" ]; then
    echo "$combined_telemetry already exists. Removing it."
    rm "$combined_telemetry"
fi

# Check if the output file already exists
if [ -f "$combined_telesignalization" ]; then
    echo "$combined_telesignalization already exists. Removing it."
    rm "$combined_telesignalization"
fi

# Loop through all yaml files starting with 'telemetry' and append them to the output file
for file in telemetry*.yaml; do
    if [ -f "$file" ]; then
        echo "Appending $file to $combined_telemetry"
        cat "$file" >> "$combined_telemetry"
        # Add a newline to separate files
        echo "" >> "$combined_telemetry"
    fi
done

echo "Telemetry files have been concatenated into $combined_telemetry"

# Loop through all yaml files starting with 'telemetry' and append them to the output file
for file in telesignalization*.yaml; do
    if [ -f "$file" ]; then
        echo "Appending $file to $combined_telesignalization"
        cat "$file" >> "$combined_telesignalization"
        # Add a newline to separate files
        echo "" >> "$combined_telesignalization"
    fi
done

echo "Telesignalization files have been concatenated into $combined_telesignalization"
