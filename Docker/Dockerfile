# Use the official Python base image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /Nimble

# Install system packages and dependencies
RUN apt-get update \
    && apt-get install -y libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy the client code into the container
COPY client.py /app
COPY requirements.txt .

# Install the required Python packages
RUN pip3 install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y libgl1-mesa-glx

# Run client.py when the Docker container launches
CMD ["python", "client.py"]
