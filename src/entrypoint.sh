#!/bin/sh

# check if RS485_REMOTE_IP and RS485_REMOTE_PORT are set, start socat and then the script
if [ -n "$RS485_REMOTE_IP" ] && [ -n "$RS485_REMOTE_PORT" ]; then
    socat pty,link=/tmp/vcom0,raw tcp:$RS485_REMOTE_IP:$RS485_REMOTE_PORT,retry,interval=.2,forever & python fetch_bms_data.py
# start only the script for locally connected RS485 devices
else
    python fetch_bms_data.py
fi
