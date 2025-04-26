#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

echo "Installing TV Player..."

# Get the absolute path of the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Ensure proper ownership of the project directory
echo "Setting correct ownership..."
chown -R pi:pi "$SCRIPT_DIR"
chmod -R 755 "$SCRIPT_DIR"

# Special permissions for uploads and frames directories
echo "Setting up media directories..."
mkdir -p "$SCRIPT_DIR/uploads"
mkdir -p "$SCRIPT_DIR/frames"
mkdir -p "$SCRIPT_DIR/static"
chown -R pi:pi "$SCRIPT_DIR/uploads" "$SCRIPT_DIR/frames" "$SCRIPT_DIR/static"
chmod -R 775 "$SCRIPT_DIR/uploads" "$SCRIPT_DIR/frames" "$SCRIPT_DIR/static"

# Install the service file
echo "Installing systemd service..."
cp "$SCRIPT_DIR/tvplayer.service" /etc/systemd/system/
chmod 644 /etc/systemd/system/tvplayer.service

# Reload systemd and enable/restart service
echo "Configuring service..."
systemctl daemon-reload
systemctl enable tvplayer
systemctl restart tvplayer

echo "Installation complete! The TV Player should now be running."
echo "Check status with: sudo systemctl status tvplayer" 