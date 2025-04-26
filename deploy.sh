#!/bin/bash
set -e

echo "Installing/updating system dependencies..."
sudo apt update
sudo apt install -y python3-pip python3-dev python3-flask python3-pil python3-numpy ffmpeg

echo "Installing PyInstaller (via pip)..."
sudo pip3 install --no-cache-dir pyinstaller

echo "Pulling latest code..."
git pull

echo "Cleaning old build..."
rm -rf dist/ build/ tvlocal.spec

echo "Building fresh binary..."
pyinstaller --onefile --name tvlocal main.py

echo "Stopping service..."
sudo systemctl stop tv.local

echo "Replacing old binary..."
sudo cp dist/tvlocal /home/pi/tv.local/tvlocal
sudo chmod +x /home/pi/tv.local/tvlocal

echo "Starting service..."
sudo systemctl start tv.local

echo "Deployment complete!"

# Create necessary directories
mkdir -p uploads frames static

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