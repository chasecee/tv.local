#!/bin/bash
set -e

# Function to check internet connectivity
check_internet() {
    if ping -c 1 1.1.1.1 >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to install dependencies
install_dependencies() {
    if check_internet; then
        echo "Internet available, updating system packages..."
        sudo apt update
        sudo apt install -y python3-pip python3-dev python3-pil python3-numpy ffmpeg
    else
        echo "No internet connection. Checking if required packages are installed..."
        if ! command -v python3 >/dev/null || ! command -v ffmpeg >/dev/null; then
            echo "ERROR: Critical packages (python3, ffmpeg) missing and no internet to install them."
            echo "Please connect to internet or install packages manually:"
            echo "sudo apt install python3-pip python3-dev python3-pil python3-numpy ffmpeg"
            exit 1
        fi
        echo "Required packages found, proceeding with offline deployment..."
    fi
}

# Install dependencies
install_dependencies

# Create directories
echo "Setting up directories..."
sudo mkdir -p /home/pi/tv.headless/{videos,frames}
sudo chown -R pi:pi /home/pi/tv.headless/

# Copy the player script
echo "Installing player script..."
sudo cp player.py /home/pi/tv.headless/
sudo chmod +x /home/pi/tv.headless/player.py

# Copy the display library
echo "Copying LCD library..."
sudo cp -r ../lib /home/pi/tv.headless/

# Create systemd service
echo "Installing systemd service..."
cat > tv.headless.service << EOF
[Unit]
Description=Headless TV Player
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/tv.headless
ExecStart=/home/pi/tv.headless/player.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo cp tv.headless.service /etc/systemd/system/
sudo systemctl daemon-reload

echo "Starting service..."
sudo systemctl enable tv.headless
sudo systemctl start tv.headless

echo "Headless deployment complete! 🎉"
echo "To add videos, copy MP4 files to /home/pi/tv.headless/videos/"
echo "Service status:"
systemctl status tv.headless --no-pager 