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

# Function to check if headless version is running
check_headless_service() {
    if systemctl is-active --quiet tv.headless; then
        echo "WARNING: Headless version (tv.headless) is running."
        read -p "Do you want to stop the headless version and continue? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo systemctl stop tv.headless
            return 0
        else
            echo "Installation aborted."
            exit 1
        fi
    fi
    return 0
}

# Function to install dependencies with offline fallback
install_dependencies() {
    if check_internet; then
        echo "Internet available, updating system packages..."
        sudo apt update
        sudo apt install -y python3-pip python3-dev python3-flask python3-pil python3-numpy ffmpeg
    else
        echo "No internet connection. Checking if required packages are installed..."
        # Check for critical packages
        if ! command -v python3 >/dev/null || ! command -v ffmpeg >/dev/null; then
            echo "ERROR: Critical packages (python3, ffmpeg) missing and no internet to install them."
            echo "Please connect to internet or install packages manually:"
            echo "sudo apt install python3-pip python3-dev python3-flask python3-pil python3-numpy ffmpeg"
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

# Check if headless version is running
check_headless_service

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
if command -v pyinstaller &> /dev/null; then
    pyinstaller --onefile --name tvlocal app.py
else
    ~/.local/bin/pyinstaller --onefile --name tvlocal app.py
fi

# Install systemd service if it doesn't exist
if [ ! -f /etc/systemd/system/tv.local.service ]; then
    echo "Installing systemd service..."
    sudo cp tv.local.service /etc/systemd/system/tv.local.service
    sudo systemctl daemon-reload
fi

echo "Stopping service..."
sudo systemctl stop tv.local || true

echo "Setting up application..."
# Create necessary directories if they don't exist
sudo mkdir -p /home/pi/tv.local/{uploads,frames,static}
sudo chown -R pi:pi /home/pi/tv.local/

# Copy the binary and set permissions
echo "Installing new binary..."
sudo cp dist/tvlocal /home/pi/tv.local/
sudo chmod +x /home/pi/tv.local/tvlocal

# Copy static assets and templates if they exist
if [ -d "static" ]; then
    echo "Copying static assets..."
    src_dir="$(pwd)/static"
    dest_dir="/home/pi/tv.local/static"
    
    if [ "$src_dir" != "$dest_dir" ]; then
        # Remove old static files first
        sudo rm -rf "$dest_dir"
        sudo cp -r "$src_dir" "/home/pi/tv.local/"
        echo "Static assets updated."
    else
        echo "Source and destination are the same, skipping static assets copy."
    fi
fi
if [ -d "templates" ]; then
    echo "Copying templates..."
    # Get absolute paths to avoid self-copying
    src_dir="$(pwd)/templates"
    dest_dir="/home/pi/tv.local/templates"
    
    # Only copy if source and destination are different
    if [ "$src_dir" != "$dest_dir" ]; then
        # Remove old templates first to ensure clean state
        sudo rm -rf "$dest_dir"
        sudo cp -r "$src_dir" "/home/pi/tv.local/"
        echo "Templates updated."
    else
        echo "Source and destination are the same, skipping template copy."
    fi
fi
if [ -d "lib" ]; then
    echo "Copying LCD library..."
    src_dir="$(pwd)/lib"
    dest_dir="/home/pi/tv.local/lib"
    
    if [ "$src_dir" != "$dest_dir" ]; then
        # Remove old lib files first
        sudo rm -rf "$dest_dir"
        sudo cp -r "$src_dir" "/home/pi/tv.local/"
        echo "LCD library updated."
    else
        echo "Source and destination are the same, skipping LCD library copy."
    fi
fi

echo "Starting service..."
sudo systemctl enable tv.local || true
sudo systemctl start tv.local

echo "Deployment complete! 🎉"

# Show service status
echo "Service status:"
systemctl status tv.local --no-pager

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