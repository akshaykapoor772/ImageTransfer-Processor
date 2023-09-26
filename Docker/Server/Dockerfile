FROM python:3.10.9

# Install system dependencies
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0

# Set working directory
WORKDIR /Nimble

# Copy the server code into the container
COPY server.py .
COPY requirements.txt .

# Install the required packages
RUN pip3 install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y libgl1-mesa-glx

# Run the server.py script when the container launches
CMD ["python3", "server.py"]
