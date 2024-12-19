#!/bin/bash

# Function to check if Pepper's NAOqi service is available
function check_naoqi {
    /usr/bin/python -c "import socket; s = socket.socket(); s.settimeout(1); s.connect(('127.0.0.1', 9559))" 2>/dev/null
}

# Wait until NAOqi is available
while ! check_naoqi; do
    echo "Waiting for NAOqi service to be available..."
    sleep 5
done

echo "NAOqi service is available. Starting Pepper server."

cd /home/nao/pepper_project

# Run the Python script using the virtual environment's Python interpreter
/home/nao/pepper_project/venv/bin/python /home/nao/pepper_project/pepper_server.py
