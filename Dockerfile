# Use an official Python runtime as a parent image
FROM python:3.8-alpine

# Install socat
RUN apk add --no-cache socat

# Set the working directory in the container
WORKDIR /usr/src/app

# Install Python modules needed by the app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /usr/src/app
COPY ./src .

# Define default environment variables
ENV PYTHONUNBUFFERED 1
ENV RS485_REMOTE_IP=192.168.1.200
ENV RS485_REMOTE_PORT=4196


# Run socat in the background and then execute app.py
CMD socat pty,link=/tmp/vcom0,raw tcp:$RS485_REMOTE_IP:$RS485_REMOTE_PORT,retry,interval=.2,forever & python fetch_bms_data.py
