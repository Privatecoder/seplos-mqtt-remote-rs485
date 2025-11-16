FROM python:3.12-alpine

# Install system packages only
RUN apk add --no-cache \
    socat \
    bash \
    jq

# Install Python dependencies with pip (for the correct Python)
RUN pip install --no-cache-dir \
    paho-mqtt \
    pyserial

# Set the working directory in the container
WORKDIR /usr/src/app

COPY src/fetch_bms_data.py ./
COPY src/ha_auto_discovery.py ./
COPY src/entrypoint.sh ./

# Make sure entrypoint is executable
RUN chmod a+x ./entrypoint.sh

# Set the entrypoint script as the entry point
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]