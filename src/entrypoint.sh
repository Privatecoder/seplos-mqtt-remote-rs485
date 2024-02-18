#!/bin/sh

# Function to handle SIGTERM
cleanup() {
    echo "Container stopped, cleaning up..."
    # Send SIGTERM to the Python script
    kill -s SIGTERM $!
    wait $!
}

# Trap SIGTERM and call cleanup function
trap cleanup SIGTERM

# start socat for master if RS485_MASTER_REMOTE_IP and RS485_MASTER_REMOTE_PORT are set
if [ -n "$RS485_MASTER_REMOTE_IP" ] && [ -n "$RS485_MASTER_REMOTE_PORT" ]; then
    echo "starting socat for master rs485 vcom ${RS485_MASTER_REMOTE_IP}:${RS485_MASTER_REMOTE_PORT}"
    socat pty,link=/tmp/vcom0,raw tcp:$RS485_MASTER_REMOTE_IP:$RS485_MASTER_REMOTE_PORT,retry,interval=.2,forever &
fi

# start socat for slaves if RS485_SLAVES_REMOTE_IP and RS485_SLAVES_REMOTE_PORT are set´
if [ -n "$RS485_SLAVES_REMOTE_IP" ] && [ -n "$RS485_SLAVES_REMOTE_PORT" ]; then
    echo "starting socat for slaves rs485 vcom ${RS485_SLAVES_REMOTE_IP}:${RS485_SLAVES_REMOTE_PORT}"
    socat pty,link=/tmp/vcom1,raw tcp:$RS485_SLAVES_REMOTE_IP:$RS485_SLAVES_REMOTE_PORT,retry,interval=.2,forever &
fi

# start the script
echo "start the script"

# run the script in background
python fetch_bms_data.py &

# wait for the script to exit
wait $!