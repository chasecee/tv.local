#!/bin/bash
set -e

# Function to check internet connectivity
check_internet() {
    # Try to reach a reliable server (Cloudflare DNS)
    if ping -c 1 1.1.1.1 >/dev/null 2>&1; then
        return 0  # Internet available
    else
        return 1  # No internet
    fi
}

# Function to install dependencies with offline fallback
install_dependencies() {
    if check_internet; then
        echo "Internet available, updating system packages..."
        sudo apt update
        sudo apt install -y python3-pip python3-dev python3-flask python3-pil python3-numpy ffmpeg pigpio python3-pigpio python3-gpiozero python3-rpi.gpio
        # Start and enable pigpio daemon
        sudo systemctl enable pigpiod
        sudo systemctl start pigpiod
        # Add user to necessary groups
        sudo usermod -a -G gpio,i2c,spi pi
        # Ensure pigpiod is running
        if ! systemctl is-active --quiet pigpiod; then
            echo "Starting pigpiod service..."
            sudo systemctl start pigpiod
            sleep 2  # Give it a moment to start
        fi
        # Verify pigpiod is actually running
        if ! pgrep pigpiod > /dev/null; then
            echo "WARNING: pigpiod process not found, attempting manual start..."
            sudo pigpiod
            sleep 2
        fi
        # Final verification
        if ! pgrep pigpiod > /dev/null; then
            echo "ERROR: Failed to start pigpiod. This is required for the LCD display."
            exit 1
        fi
    else
        echo "No internet connection. Checking if required packages are installed..."
        # Check for critical packages
        if ! command -v python3 >/dev/null || ! command -v ffmpeg >/dev/null; then
            echo "ERROR: Critical packages (python3, ffmpeg) missing and no internet to install them."
            echo "Please connect to internet or install packages manually:"
            echo "sudo apt install python3-pip python3-dev python3-flask python3-pil python3-numpy ffmpeg pigpio python3-pigpio python3-gpiozero python3-rpi.gpio"
            exit 1
        fi
        echo "Required packages found, proceeding with offline deployment..."
    fi
}

# Function to install PyInstaller with offline fallback
install_pyinstaller() {
    if ! command -v pyinstaller &> /dev/null; then
        if check_internet; then
            echo "Installing PyInstaller..."
            # Try user installation first
            pip3 install --user pyinstaller || {
                echo "User installation failed, trying system-wide..."
                sudo pip3 install pyinstaller
            }
        else
            echo "ERROR: PyInstaller not found and no internet to install it."
            echo "Please connect to internet or install PyInstaller manually:"
            echo "sudo pip3 install --break-system-packages pyinstaller"
            exit 1
        fi
    else
        echo "PyInstaller already installed, proceeding..."
    fi
}

# Install dependencies
install_dependencies

# Install PyInstaller
install_pyinstaller

# Add local bin to PATH for this session
export PATH="$HOME/.local/bin:$PATH"

# Optional git pull
if check_internet; then
    echo "Pulling latest code..."
    git pull || echo "Git pull failed, using existing code..."
else
    echo "No internet connection, using existing code..."
fi

echo "Cleaning old build..."
rm -rf dist/ build/ tvlocal.spec

echo "Building fresh binary..."
# Generate spec file if it doesn't exist
if [ ! -f "tvlocal.spec" ]; then
    echo "Generating PyInstaller spec file..."
    # Optimize for Pi Zero 2W
    export PYTHONOPTIMIZE=2  # Enable Python optimizations
    export PYTHONDONTWRITEBYTECODE=1  # Don't create .pyc files
    export PYTHONHASHSEED=0  # Make Python's hash randomization deterministic
    
    pyinstaller --name tvlocal --onedir \
        --add-data "static:static" \
        --add-data "templates:templates" \
        --add-data "lib:lib" \
        --add-data "web:web" \
        --add-data "images:images" \
        --add-data "video:video" \
        --add-data "/usr/lib/python3/dist-packages/gpiozero:gpiozero" \
        --add-data "/usr/lib/python3/dist-packages/RPi:RP" \
        --hidden-import flask \
        --hidden-import PIL \
        --hidden-import numpy \
        --hidden-import display \
        --hidden-import gpiozero \
        --hidden-import gpiozero.pins.lgpio \
        --hidden-import gpiozero.pins.rpigpio \
        --hidden-import gpiozero.pins.pigpio \
        --hidden-import gpiozero.pins.native \
        --hidden-import spidev \
        --hidden-import RPi.GPIO \
        --hidden-import lgpio \
        --hidden-import pigpio \
        --hidden-import numbers \
        --hidden-import argparse \
        --hidden-import atexit \
        --hidden-import shutil \
        --hidden-import subprocess \
        --hidden-import socket \
        --hidden-import glob \
        --hidden-import threading \
        --hidden-import Image \
        --hidden-import ImageDraw \
        --hidden-import ImageFont \
        --hidden-import gpiozero.pins.local \
        --hidden-import gpiozero.pins.mock \
        --hidden-import gpiozero.pins.rpio \
        --hidden-import gpiozero.pins.rpigpio \
        --hidden-import gpiozero.pins.pigpio \
        --hidden-import gpiozero.pins.lgpio \
        --hidden-import gpiozero.pins.native \
        --hidden-import gpiozero.pins.pi \
        --hidden-import gpiozero.pins.rpi \
        --hidden-import gpiozero.pins.rpio \
        --hidden-import gpiozero.pins.rpigpio \
        --hidden-import gpiozero.pins.pigpio \
        --hidden-import gpiozero.pins.lgpio \
        --hidden-import gpiozero.pins.native \
        --noconfirm \
        --clean \
        --strip \
        --log-level DEBUG \
        --exclude-module matplotlib \
        --exclude-module tkinter \
        --exclude-module PyQt5 \
        --exclude-module PySide2 \
        --exclude-module pandas \
        --exclude-module scipy \
        --exclude-module sklearn \
        --exclude-module tensorflow \
        --exclude-module torch \
        --exclude-module cv2 \
        --exclude-module pygame \
        --exclude-module wx \
        --exclude-module PyGObject \
        --exclude-module gi \
        --exclude-module dbus \
        --exclude-module _tkinter \
        --exclude-module _gtkagg \
        --exclude-module _agg2 \
        --exclude-module _cairo \
        --exclude-module _curses \
        --exclude-module _decimal \
        --exclude-module _hashlib \
        --exclude-module _lzma \
        --exclude-module _multiprocessing \
        --exclude-module _opcode \
        --exclude-module _posixsubprocess \
        --exclude-module _ssl \
        --exclude-module _testcapi \
        --exclude-module _uuid \
        app.py
else
    echo "Using existing spec file..."
    pyinstaller --noconfirm --clean tvlocal.spec
fi

# Verify the build was successful
if [ ! -f "dist/tvlocal" ]; then
    echo "ERROR: PyInstaller build failed!"
    exit 1
fi

echo "Build successful! Binary size: $(du -h dist/tvlocal | cut -f1)"

# Install systemd service (force replace)
echo "Installing/updating systemd service..."
sudo cp tv.local.service /etc/systemd/system/tv.local.service
sudo systemctl daemon-reload
sudo systemctl restart tv.local

echo "Stopping service..."
sudo systemctl stop tv.local || true

echo "Setting up application..."
# Create necessary directories if they don't exist
sudo mkdir -p /home/pi/tv.local/{uploads,frames,static,video}
sudo chown -R pi:pi /home/pi/tv.local/

# Copy the binary and set permissions
echo "Installing new binary..."
sudo cp dist/tvlocal /home/pi/tv.local/
sudo chmod +x /home/pi/tv.local/tvlocal

# Copy static assets and templates if they exist
if [ -d "static" ]; then
    echo "Copying static assets..."
    sudo cp -r static/* /home/pi/tv.local/static/
fi
if [ -d "templates" ]; then
    echo "Copying templates..."
    sudo cp -r templates /home/pi/tv.local/
fi
if [ -d "lib" ]; then
    echo "Copying LCD library..."
    sudo cp -r lib /home/pi/tv.local/
fi
if [ -d "video" ]; then
    echo "Copying default videos..."
    sudo cp -r video /home/pi/tv.local/
fi

echo "Starting service..."
sudo systemctl enable tv.local || true
sudo systemctl start tv.local

echo "Deployment complete! 🎉"

# Show service status
echo "Service status:"
systemctl status tv.local --no-pager

# Add automatic error recovery
echo "Setting up automatic error recovery..."
cat > /home/pi/tv.local/health_check.sh << 'EOL'
#!/bin/bash
while true; do
    if ! systemctl is-active --quiet tv.local; then
        echo "$(date) - Service not running, attempting restart..."
        sudo systemctl restart tv.local
    fi
    sleep 60
done
EOL

chmod +x /home/pi/tv.local/health_check.sh

# Create a systemd service for health check
cat > /etc/systemd/system/tv.health.service << 'EOL'
[Unit]
Description=TV Local Health Check Service
After=network.target tv.local.service

[Service]
Type=simple
ExecStart=/home/pi/tv.local/health_check.sh
Restart=always
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
EOL

# Enable and start health check service
sudo systemctl daemon-reload
sudo systemctl enable tv.health
sudo systemctl start tv.health

echo "Appliance setup complete! The system will:"
echo "1. Automatically restart if the service stops"
echo "2. Monitor system health every minute"
echo "3. Auto-recover from common errors"

# Final status check
echo "Current status:"
systemctl status tv.local --no-pager
systemctl status tv.health --no-pager

# Check for FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ffmpeg
    elif [[ -f /etc/debian_version ]]; then
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    else
        echo "Error: Unsupported system. Please install FFmpeg manually."
        exit 1
    fi
fi

# Set permissions
chmod +x tvlocal

# Start the application
echo "Starting TV Local application..."
./tvlocal 