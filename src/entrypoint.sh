#!/usr/bin/env bash
set -Eeuo pipefail

###############################################################################
# Logging
###############################################################################
log()  { printf '%s %s\n' "[$(date +'%Y-%m-%d %H:%M:%S%z')]" "$*"; }
info() { log "INFO: $*"; }
warn() { log "WARN: $*"; }
err()  { log "ERROR: $*" >&2; }

###############################################################################
# Helpers
###############################################################################
require_env() {
  # usage: require_env VAR [friendly name]
  local var="$1"
  local name="${2:-$1}"
  if [[ -z "${!var:-}" ]]; then
    err "Required environment variable '$name' is not set."
    MISSING=1
  fi
}

require_cmd() {
  # usage: require_cmd cmd
  if ! command -v "$1" >/dev/null 2>&1; then
    err "Required command '$1' not found."
    MISSING=1
  fi
}

###############################################################################
# Defaults (can be overridden via ENV)
###############################################################################
: "${LOGGING_LEVEL:=info}"
: "${MQTT_UPDATE_INTERVAL:=1}"        # seconds
: "${ENABLE_HA_DISCOVERY_CONFIG:=false}"
: "${INVERT_HA_DIS_CHARGE_MEASUREMENTS:=false}"
: "${HA_DISCOVERY_PREFIX:=homeassistant}"

###############################################################################
# Validate required / conditional environment variables
###############################################################################
MISSING=0

# Always required
require_env SERIAL_INTERFACE
require_env NUMBER_OF_PACKS
require_env MIN_CELL_VOLTAGE
require_env MAX_CELL_VOLTAGE
require_env MQTT_HOST
require_env MQTT_PORT
require_env MQTT_USERNAME
require_env MQTT_PASSWORD
require_env MQTT_TOPIC

# Optional: RS485 remote mode; if IP is set, port is mandatory and socat is required
if [[ -n "${RS485_REMOTE_IP:-}" ]]; then
  require_env RS485_REMOTE_PORT
  require_cmd socat
else
  # Local interface: check if the device exists (warn only if not)
  if [[ -e "${SERIAL_INTERFACE}" ]]; then
    :
  else
    warn "SERIAL_INTERFACE '${SERIAL_INTERFACE}' does not exist (yet)."
    warn "If a USB serial adapter appears later, this warning can be ignored."
  fi
fi

# Python required
require_cmd python3

if [[ "${MISSING}" -ne 0 ]]; then
  err "Aborting due to missing requirements. Please check environment variables and dependencies."
  exit 1
fi

###############################################################################
# Start
###############################################################################
info "Starting Seplos MQTT RS485..."

# Optionally: start remote RS485 connection via socat
if [[ -n "${RS485_REMOTE_IP:-}" ]]; then
  info "Configuring remote RS485: ${RS485_REMOTE_IP}:${RS485_REMOTE_PORT} -> ${SERIAL_INTERFACE}"
  # create a PTY and link it to SERIAL_INTERFACE
  socat "pty,link=${SERIAL_INTERFACE},raw,echo=0" \
        "tcp:${RS485_REMOTE_IP}:${RS485_REMOTE_PORT},retry,interval=.2,forever" &
  SOCAT_PID=$!
  # short delay to ensure the link is ready
  sleep 2
else
  info "Using local serial interface: ${SERIAL_INTERFACE}"
fi

# Debug output
if [[ "${LOGGING_LEVEL}" == "debug" ]]; then
  info "Debug configuration:"
  log "  RS485_REMOTE_IP=${RS485_REMOTE_IP:-<empty>}"
  log "  RS485_REMOTE_PORT=${RS485_REMOTE_PORT:-<empty>}"
  log "  SERIAL_INTERFACE=${SERIAL_INTERFACE}"
  log "  NUMBER_OF_PACKS=${NUMBER_OF_PACKS}"
  log "  MIN_CELL_VOLTAGE=${MIN_CELL_VOLTAGE}"
  log "  MAX_CELL_VOLTAGE=${MAX_CELL_VOLTAGE}"
  log "  MQTT_HOST=${MQTT_HOST}"
  log "  MQTT_PORT=${MQTT_PORT}"
  log "  MQTT_USERNAME=${MQTT_USERNAME}"
  log "  MQTT_TOPIC=${MQTT_TOPIC}"
  log "  MQTT_UPDATE_INTERVAL=${MQTT_UPDATE_INTERVAL}"
  log "  ENABLE_HA_DISCOVERY_CONFIG=${ENABLE_HA_DISCOVERY_CONFIG}"
  log "  HA_DISCOVERY_PREFIX=${HA_DISCOVERY_PREFIX}"
  log "  INVERT_HA_DIS_CHARGE_MEASUREMENTS=${INVERT_HA_DIS_CHARGE_MEASUREMENTS}"
  log "  LOGGING_LEVEL=${LOGGING_LEVEL}"
fi

info "Starting Seplos BMS data fetcher..."
# Start the Python script with current environment variables
exec python3 -u /usr/src/app/fetch_bms_data.py