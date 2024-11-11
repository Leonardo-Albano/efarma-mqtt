# Use a base Python image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the application code to the container
COPY . .

# Install required Python packages
RUN pip install --no-cache-dir paho-mqtt requests flask

# Expose the port Flask will run on
EXPOSE 5002

# Start the application
CMD ["python", "mqtt_server.py"]
