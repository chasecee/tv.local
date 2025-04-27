# Headless TV Player

A simplified version of the TV Player that runs without a web interface. Just drop MP4 files in the videos directory and they'll play automatically.

## Quick Start

1. **Hardware Setup**

   ```bash
   # Enable SPI on Raspberry Pi
   sudo raspi-config nonint do_spi 0
   ```

2. **Deploy**

   ```bash
   cd headless
   ./deploy.sh
   ```

3. **Add Videos**
   ```bash
   # Copy your MP4 file to the videos directory
   sudo cp your_video.mp4 /home/pi/tv.headless/videos/
   ```

## Directory Structure

```
/home/pi/tv.headless/
├── tvheadless     # Compiled binary
├── videos/        # Drop your MP4 files here
├── frames/        # Converted frames (managed automatically)
└── lib/           # LCD driver
```

## Service Management

```bash
# Check status
sudo systemctl status tv.headless

# Stop service
sudo systemctl stop tv.headless

# Start service
sudo systemctl start tv.headless

# View logs
sudo journalctl -fu tv.headless
```

## Default Video

To set a default video that plays on startup:

```bash
echo "your_video.mp4" | sudo tee /home/pi/tv.headless/.default_video
```

## Switching Between Versions

You can't run both the web and headless versions simultaneously. To switch:

1. Stop current version:

   ```bash
   sudo systemctl stop tv.local    # If running web version
   # or
   sudo systemctl stop tv.headless # If running headless version
   ```

2. Start desired version:
   ```bash
   sudo systemctl start tv.local    # For web version
   # or
   sudo systemctl start tv.headless # For headless version
   ```
