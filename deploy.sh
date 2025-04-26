#!/bin/bash
set -e

echo "Installing/updating system dependencies..."
sudo apt update
sudo apt install -y python3-pip python3-dev python3-flask python3-pil python3-numpy ffmpeg

echo "Installing PyInstaller system-wide..."
# Full send with sudo pip - it's a dedicated Pi after all! 🚀
sudo pip3 install --break-system-packages pyinstaller

# Add local bin to PATH for this session
export PATH="$HOME/.local/bin:$PATH"

echo "Pulling latest code..."
git pull

echo "Cleaning old build..."
rm -rf dist/ build/ tvlocal.spec

echo "Building fresh binary..."
# Use full path to pyinstaller if PATH update doesn't take effect
if command -v pyinstaller &> /dev/null; then
    pyinstaller --onefile --name tvlocal app.py
else
    ~/.local/bin/pyinstaller --onefile --name tvlocal app.py
fi

# Install systemd service if it doesn't exist
if [ ! -f /etc/systemd/system/tv.local.service ]; then
    echo "Installing systemd service..."
    sudo cp tvplayer.service /etc/systemd/system/tv.local.service
    sudo systemctl daemon-reload
fi

echo "Stopping service..."
sudo systemctl stop tv.local || true  # Don't fail if service doesn't exist

echo "Setting up application..."
# Create necessary directories if they don't exist
sudo mkdir -p /home/pi/tv.local/{uploads,frames,static}
sudo chown -R pi:pi /home/pi/tv.local/

# Copy the binary and set permissions
echo "Installing new binary..."
sudo cp dist/tvlocal /home/pi/tv.local/
sudo chmod +x /home/pi/tv.local/tvlocal

echo "Starting service..."
sudo systemctl enable tv.local || true  # Enable service to start on boot
sudo systemctl start tv.local || true

echo "Deployment complete! 🎉"

# Show service status
echo "Service status:"
sudo systemctl status tv.local || true

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
chmod +x tv-local

# Start the application
echo "Starting TV Local application..."
./tv-local 