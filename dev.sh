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

# Function to setup virtual environment
setup_venv() {
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    echo "Activating virtual environment..."
    source venv/bin/activate
    
    echo "Upgrading pip..."
    pip install --upgrade pip
}

# Function to install dependencies
install_dependencies() {
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
}

# Function to setup directories
setup_directories() {
    echo "Setting up directories..."
    if [ "$MODE" = "web" ]; then
        mkdir -p web/{uploads,frames,static}
    else
        mkdir -p headless/videos
    fi
}

# Main function
run_dev() {
    # Check if other version is running
    check_other_service

    # Setup virtual environment
    setup_venv

    # Install dependencies
    install_dependencies

    # Setup directories
    setup_directories

    # Run the appropriate mode
    if [ "$MODE" = "web" ]; then
        echo "Starting web development server on port 8080..."
        venv/bin/python web/app.py --port 8080
    else
        echo "Starting headless development server..."
        venv/bin/python headless/main.py
    fi
}

# Run development server
run_dev 