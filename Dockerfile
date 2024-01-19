FROM python:3.8-alpine

# Install socat
RUN apk add --no-cache socat

# Set the working directory in the container
WORKDIR /usr/src/app

# Install required Python modules
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the src directory contents into the container at /usr/src/app
COPY ./src .

# Define default environment variables
ENV PYTHONUNBUFFERED 1

# Make sure entrypoint is executable
RUN chmod +x /usr/src/app/entrypoint.sh

# Set the entrypoint script as the entry point
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]