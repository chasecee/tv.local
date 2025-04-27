#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

echo "Installing TV Local..."

# Get the absolute path of the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Function to check internet connectivity
check_internet() {
    if ping -c 1 1.1.1.1 >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to install dependencies with offline fallback
install_dependencies() {
    if check_internet; then
        echo "Internet available, updating system packages..."
        sudo apt update
        sudo apt install -y python3-pip python3-dev python3-flask python3-pil python3-numpy ffmpeg
    else
        echo "No internet connection. Checking if required packages are installed..."
        if ! command -v python3 >/dev/null || ! command -v ffmpeg >/dev/null; then
            echo "ERROR: Critical packages (python3, ffmpeg) missing and no internet to install them."
            echo "Please connect to internet or install packages manually:"
            echo "sudo apt install python3-pip python3-dev python3-flask python3-pil python3-numpy ffmpeg"
            exit 1
        fi
        echo "Required packages found, proceeding with offline installation..."
    fi
}

# Function to install PyInstaller with offline fallback
install_pyinstaller() {
    if ! command -v pyinstaller &> /dev/null; then
        if check_internet; then
            echo "Installing PyInstaller system-wide..."
            sudo pip3 install --break-system-packages pyinstaller
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
install_pyinstaller

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
cp "$SCRIPT_DIR/tv.local.service" /etc/systemd/system/tv.local.service
chmod 644 /etc/systemd/system/tv.local.service

# Reload systemd and enable/restart service
echo "Configuring service..."
systemctl daemon-reload
systemctl enable tv.local

echo "Installation complete! 🎉"
echo "Next steps:"
echo "1. Run ./deploy.sh to build and deploy the application"
echo "2. Start the service with: sudo systemctl start tv.local"
echo "3. Check status with: sudo systemctl status tv.local" 