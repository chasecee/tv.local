# Mini TV Player

A self-contained video player for Raspberry Pi Zero 2W that displays looping video content on a 2" LCD screen. Features a web UI for video management and compiles to a single binary for maximum reliability.

## Features

- 🎥 Video playback on 2" SPI LCD (320x240)
- 🌐 Web UI at `http://tv.local`
- 📤 Upload and manage MP4 files
- 🔄 Automatic video-to-frames conversion
- 🚀 Single-binary deployment
- 🔌 Power-loss resistant
- 🎯 12 FPS smooth playback
- 🎬 Ships with default video

## Quick Start (Pi Zero 2W - Bookworm)

1. **Hardware Setup**

   ```bash
   # Enable SPI on Raspberry Pi
   sudo raspi-config nonint do_spi 0
   ```

2. **Install Dependencies**

   ```bash
   sudo apt update
   sudo apt install -y ffmpeg git python3-pip python3-flask python3-pil python3-numpy
   ```

3. **Get Code & Test**

   ```bash
   git clone https://github.com/chasecee/tv.local.git
   cd tv.local
   python3 app.py  # Test on port 5000
   ```

4. **Deploy for Production**

   ```bash
   ./deploy.sh  # Creates binary & installs service
   ```

5. **Access**
   - Development: `http://<PI_IP_ADDRESS>:5000`
   - Production: `http://tv.local` or `http://<PI_IP_ADDRESS>`
   - Default video (`wonka.mp4`) will play automatically
   - Upload new videos through web UI

## Project Structure

```
tv.local/
├── app.py              # Main application
├── display.py          # LCD display handler
├── deploy.sh           # Deployment script
├── tvplayer.service    # Systemd service
├── static/             # Web UI assets
├── templates/          # Flask templates
├── video/             # Default videos (included in repo)
├── uploads/            # User video storage (created on run)
├── frames/             # Converted frames (created on run)
└── lib/                # LCD driver
```

## Video Management

- **Default Video**:

  - The repo includes `wonka.mp4` as default video
  - Stored in `video/` directory
  - Automatically copied to `uploads/` on first run
  - Set as default if no other default exists

- **Custom Videos**:
  - Upload through web UI
  - Stored in `uploads/` directory
  - Set any video as default through web UI
  - All videos automatically converted to frames

## Troubleshooting

- **Service Issues**

  ```bash
  sudo systemctl status tv.local
  sudo journalctl -fu tv.local
  ```

- **Common Problems**
  - Web UI not accessible: Check service status
  - Upload fails: Check directory permissions
  - LCD not working: Verify SPI is enabled
  - Frames not showing: Check logs with `journalctl`

## System Optimization (Optional)

```bash
# Disable unused services
sudo systemctl disable --now bluetooth

# Reduce GPU memory (headless)
sudo raspi-config nonint do_memory_split 16

# Disable HDMI to save power
echo "hdmi_ignore_hotplug=1" | sudo tee -a /boot/config.txt
```

## License

MIT License - See LICENSE file for details
