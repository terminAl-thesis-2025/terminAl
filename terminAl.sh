#!/bin/bash
# Get the absolute path to your application directory
APP_DIR="/home/m/PycharmProjects/terminAl"

# Change to the application directory
cd "$APP_DIR"

# Determine which Python executable to use
if [ -f "$APP_DIR/.venv/bin/python3" ]; then
  PYTHON="$APP_DIR/.venv/bin/python3"
elif [ -f "$APP_DIR/.venv/bin/python" ]; then
  PYTHON="$APP_DIR/.venv/bin/python"
else
  echo "Could not find Python in the virtual environment. Please check if the venv is set up correctly."
  exit 1
fi

# Run the app with the Python from the virtual environment with sudo privileges
sudo $PYTHON main.py "$@"