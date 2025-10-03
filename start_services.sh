#!/bin/bash
# start_services.sh
# Starts the Flask web app and the print manager in the background

# Start the Flask web app
cd "$(dirname "$0")/web-app"
nohup python3 app.py > ../web-app.log 2>&1 &

# Start the print manager
cd ../src/controller
nohup python3 print_manager.py > ../../print_manager.log 2>&1 &

echo "Both services started. Access the web UI at http://<raspberry-pi-ip>:5000"