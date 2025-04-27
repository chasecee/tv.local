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

# Function to check if web version is running
check_web_service() {
    if systemctl is-active --quiet tv.local; then
        echo "WARNING: Web version (tv.local) is running."
        read -p "Do you want to stop the web version and continue? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo systemctl stop tv.local
            return 0
        else
            echo "Installation aborted."
            exit 1
        fi
    fi
    return 0
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

# Check if web version is running
check_web_service

# Install dependencies
install_dependencies

# Install PyInstaller
install_pyinstaller

# Add local bin to PATH for this session
export PATH="$HOME/.local/bin:$PATH"

echo "Building fresh binary..."
rm -rf dist/ build/ tvheadless.spec
if command -v pyinstaller &> /dev/null; then
    pyinstaller --onefile --name tvheadless player.py
else
    ~/.local/bin/pyinstaller --onefile --name tvheadless player.py
fi

# Create directories
echo "Setting up directories..."
sudo mkdir -p /home/pi/tv.headless/{videos,frames}
sudo chown -R pi:pi /home/pi/tv.headless/

# Copy the binary and set permissions
echo "Installing binary..."
sudo cp dist/tvheadless /home/pi/tv.headless/
sudo chmod +x /home/pi/tv.headless/tvheadless

# Copy the display library
echo "Copying LCD library..."
sudo cp -r ../lib /home/pi/tv.headless/

# Create state files with proper permissions
echo "Setting up state files..."
sudo touch /home/pi/tv.headless/{.last_video,.default_video,.video_marker}
sudo chown pi:pi /home/pi/tv.headless/{.last_video,.default_video,.video_marker}
sudo chmod 644 /home/pi/tv.headless/{.last_video,.default_video,.video_marker}

# Install systemd service
echo "Installing systemd service..."
sudo cp headless.service /etc/systemd/system/tv.headless.service
sudo systemctl daemon-reload

echo "Starting service..."
sudo systemctl enable tv.headless
sudo systemctl start tv.headless

echo "Headless deployment complete! 🎉"
echo "To add videos, copy MP4 files to /home/pi/tv.headless/videos/"
echo "To set a default video, create a file named .default_video with the video filename"
echo "Service status:"
systemctl status tv.headless --no-pager 