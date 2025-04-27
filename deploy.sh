#!/bin/bash
set -e

# Default to web mode
MODE="web"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --headless)
            MODE="headless"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Function to check internet connectivity
check_internet() {
    if ping -c 1 1.1.1.1 >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to check if other version is running
check_other_service() {
    if [ "$MODE" = "web" ]; then
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
    else
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
    fi
    return 0
}

# Function to install dependencies with offline fallback
install_dependencies() {
    if check_internet; then
        echo "Internet available, updating system packages..."
        sudo apt update
        # Install packages in parallel
        sudo apt install -y python3-pip python3-dev python3-flask python3-pil python3-numpy ffmpeg libcap2-bin python3-spidev &
        PID1=$!
        wait $PID1
    else
        echo "No internet connection. Checking if required packages are installed..."
        if ! command -v python3 >/dev/null || ! command -v ffmpeg >/dev/null || ! command -v setcap >/dev/null; then
            echo "ERROR: Critical packages (python3, ffmpeg, libcap2-bin) missing and no internet to install them."
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
            exit 1
        fi
    fi
}

# Function to setup capabilities
setup_capabilities() {
    if [ "$MODE" = "web" ]; then
        echo "Setting up capabilities for port 80..."
        if command -v setcap >/dev/null 2>&1; then
            if sudo setcap 'cap_net_bind_service=+ep' "$TARGET_DIR/tvlocal"; then
                echo "Successfully set capabilities for port 80"
            else
                echo "WARNING: Failed to set capabilities for port 80"
                echo "You may need to run the service as root or use a different port"
                read -p "Do you want to use port 8080 instead? (y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    # Modify the service file to use port 8080
                    sudo sed -i 's/--port 80/--port 8080/' "/etc/systemd/system/$SERVICE_NAME.service"
                    sudo systemctl daemon-reload
                else
                    echo "Installation may fail without proper port access"
                fi
            fi
        else
            echo "WARNING: setcap command not found"
            echo "You may need to run the service as root or use a different port"
            read -p "Do you want to use port 8080 instead? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sudo sed -i 's/--port 80/--port 8080/' "/etc/systemd/system/$SERVICE_NAME.service"
                sudo systemctl daemon-reload
            else
                echo "Installation may fail without proper port access"
            fi
        fi
    fi
}

# Main deployment function
deploy() {
    # Check if other version is running
    check_other_service

    # Install dependencies and PyInstaller in parallel
    install_dependencies &
    PID1=$!
    install_pyinstaller &
    PID2=$!
    wait $PID1 $PID2

    # Add local bin to PATH
    export PATH="$HOME/.local/bin:$PATH"

    # Optional git pull if internet is available
    if check_internet; then
        echo "Pulling latest code..."
        git pull || echo "Git pull failed, using existing code..."
    fi

    # Clean and build
    echo "Cleaning old build..."
    rm -rf dist/ build/ tvlocal.spec

    if [ "$MODE" = "web" ]; then
        echo "Building web mode binary..."
        # Copy fonts for bundling
        echo "Copying fonts for bundling..."
        mkdir -p web/fonts
        cp -r python/Font/* web/fonts/
        
        # Install Python dependencies
        echo "Installing Python dependencies..."
        # No need to install anything via pip, all packages are from apt
        
        # Copy lib files to web directory
        echo "Copying lib files to web directory..."
        mkdir -p web/lib
        cp lib/*.py web/lib/
        
        # Copy lib files to headless directory
        echo "Copying lib files to headless directory..."
        mkdir -p headless/lib
        cp lib/*.py headless/lib/
        
        # Set up PyInstaller optimizations
        echo "Setting up PyInstaller optimizations..."
        export PYINSTALLER_CACHE_DIR=~/.cache/pyinstaller
        export PYTHONDONTWRITEBYTECODE=0  # Enable bytecode caching
        export PYINSTALLER_PARALLEL=4      # Use 4 parallel processes
        
        # Create cache directory if it doesn't exist
        mkdir -p "$PYINSTALLER_CACHE_DIR"
        
        pyinstaller --onefile \
            --noconfirm \
            --add-data "web/lib:LIB" \
            --add-data "web/display.py:." \
            --add-data "web/fonts:fonts" \
            --hidden-import lib.LCD_2inch \
            --hidden-import lib.lcdconfig \
            --hidden-import display \
            --hidden-import PIL \
            --hidden-import PIL.Image \
            --hidden-import PIL.ImageDraw \
            --hidden-import PIL.ImageFont \
            --name tvlocal web/app.py
            
        # Clean up fonts
        rm -rf web/fonts
        
        # Verify binary was built
        if [ ! -f "dist/tvlocal" ]; then
            echo "ERROR: PyInstaller failed to create binary at dist/tvlocal"
            exit 1
        fi
        echo "Binary built successfully at dist/tvlocal"
        SERVICE_NAME="tv.local"
        TARGET_DIR="/home/pi/tv.local/web"
    else
        echo "Building headless mode binary..."
        # Copy fonts for bundling
        echo "Copying fonts for bundling..."
        mkdir -p web/fonts
        cp -r python/Font/* web/fonts/
        
        # Install Python dependencies
        echo "Installing Python dependencies..."
        # No need to install anything via pip, all packages are from apt
        
        # Copy lib files to web directory
        echo "Copying lib files to web directory..."
        mkdir -p web/lib
        cp lib/*.py web/lib/
        
        # Copy lib files to headless directory
        echo "Copying lib files to headless directory..."
        mkdir -p headless/lib
        cp lib/*.py headless/lib/
        
        pyinstaller --onefile \
            --noconfirm \
            --add-data "web/lib:LIB" \
            --add-data "web/display.py:." \
            --add-data "web/fonts:fonts" \
            --hidden-import lib.LCD_2inch \
            --hidden-import lib.lcdconfig \
            --hidden-import display \
            --hidden-import PIL \
            --hidden-import PIL.Image \
            --hidden-import PIL.ImageDraw \
            --hidden-import PIL.ImageFont \
            --name tvheadless web/main.py
            
        # Verify binary was built
        if [ ! -f "dist/tvheadless" ]; then
            echo "ERROR: PyInstaller failed to create binary at dist/tvheadless"
            exit 1
        fi
        echo "Binary built successfully at dist/tvheadless"
        SERVICE_NAME="tv.headless"
        TARGET_DIR="/home/pi/tv.local/headless"
    fi

    # Setup service
    if [ "$MODE" = "web" ]; then
        echo "Installing systemd service..."
        # Create service file with correct paths
        cat > tv.local.service << EOF
[Unit]
Description=Mini TV Player Service
After=network.target

[Service]
# Set the working directory to the project root
WorkingDirectory=/home/pi/tv.local/web

# Run the compiled binary with port 8080
ExecStart=/home/pi/tv.local/web/tvlocal --port 8080

# Run as pi user
User=pi
Group=pi

# Restart settings
Restart=always
RestartSec=10

# Standard output and error logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
        
        sudo cp tv.local.service /etc/systemd/system/
        sudo systemctl daemon-reload
    fi

    # Stop service if running
    echo "Stopping service..."
    sudo systemctl stop "$SERVICE_NAME" || true

    # Setup directories
    echo "Setting up application..."
    if [ "$MODE" = "web" ]; then
        sudo mkdir -p "$TARGET_DIR/{uploads,frames,static}"
    else
        sudo mkdir -p "$TARGET_DIR/videos"
    fi
    sudo chown -R pi:pi /home/pi/tv.local/

    # Install binary
    echo "Installing new binary..."
    if [ "$MODE" = "web" ]; then
        echo "Copying binary to $TARGET_DIR/tvlocal..."
        sudo cp dist/tvlocal "$TARGET_DIR/"
        echo "Setting permissions..."
        sudo chown pi:pi "$TARGET_DIR/tvlocal"
        sudo chmod 755 "$TARGET_DIR/tvlocal"  # rwxr-xr-x
        
        # Verify permissions
        if [ ! -x "$TARGET_DIR/tvlocal" ]; then
            echo "ERROR: Binary not executable after setting permissions"
            exit 1
        fi
        if [ "$(stat -c '%U' "$TARGET_DIR/tvlocal")" != "pi" ]; then
            echo "ERROR: Binary not owned by pi user"
            exit 1
        fi
        echo "Binary verified at $TARGET_DIR/tvlocal"
        # Setup capabilities for web mode
        setup_capabilities
    else
        echo "Copying binary to $TARGET_DIR/tvheadless..."
        sudo cp dist/tvheadless "$TARGET_DIR/"
        echo "Setting permissions..."
        sudo chmod +x "$TARGET_DIR/tvheadless"
        # Verify binary exists and is executable
        if [ ! -f "$TARGET_DIR/tvheadless" ]; then
            echo "ERROR: Binary not found at $TARGET_DIR/tvheadless"
            exit 1
        fi
        if [ ! -x "$TARGET_DIR/tvheadless" ]; then
            echo "ERROR: Binary not executable at $TARGET_DIR/tvheadless"
            exit 1
        fi
        echo "Binary verified at $TARGET_DIR/tvheadless"
    fi

    # Copy assets in parallel if they exist
    if [ "$MODE" = "web" ]; then
        if [ -d "web/static" ]; then
            echo "Copying static assets..."
            sudo rsync -a --delete web/static/ "$TARGET_DIR/static/" &
        fi
        if [ -d "web/templates" ]; then
            echo "Copying templates..."
            sudo rsync -a --delete web/templates/ "$TARGET_DIR/templates/" &
        fi
    fi
    if [ -d "lib" ]; then
        echo "Copying LCD library..."
        sudo rsync -a --delete lib/ "$TARGET_DIR/lib/" &
    fi
    wait

    # Cleanup
    echo "Cleaning up build files..."
    if [ "$MODE" = "web" ]; then
        rm -rf web/lib
    else
        rm -rf headless/lib
    fi
    rm -rf dist/ build/ tvlocal.spec tvheadless.spec

    # Start service
    echo "Starting service..."
    sudo systemctl enable "$SERVICE_NAME" || true
    sudo systemctl start "$SERVICE_NAME"

    echo "Deployment complete! 🎉"
    systemctl status "$SERVICE_NAME" --no-pager
}

# Run deployment
deploy

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