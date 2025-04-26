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