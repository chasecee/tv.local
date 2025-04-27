# Mini TV Player

A self-contained video player for Raspberry Pi that displays looping video content on a 2" LCD screen. Available in two deployment modes:

- Web UI mode: Full web interface for video management
- Headless mode: Simple, lightweight deployment for basic playback

## Features

- 🎥 Video playback on 2" SPI LCD (320x240)
- 🌐 Web UI at `http://tv.local` (web mode only)
- 📤 Upload and manage MP4 files (web mode only)
- 🔄 Automatic video-to-frames conversion
- 🚀 Single-binary deployment
- 🔌 Power-loss resistant
- 🎯 12 FPS smooth playback

## Quick Start

1. **Hardware Setup**

   ```bash
   # Enable SPI on Raspberry Pi
   sudo raspi-config nonint do_spi 0
   ```

2. **Install Dependencies**

   ```bash
   sudo apt update
   sudo apt install -y ffmpeg git
   ```

3. **Deploy**

   ```bash
   git clone https://github.com/chasecee/tv.local.git
   cd tv.local

   # For web mode (default):
   ./deploy.sh

   # For headless mode:
   ./deploy.sh --headless
   ```

4. **Access**
   - Web mode: Open `http://tv.local` or `http://<PI_IP_ADDRESS>`
   - Headless mode: Place videos in the `headless/videos` directory

## Project Structure

```
tv.local/
├── web/                 # Web UI deployment
│   ├── app.py          # Main web application
│   ├── static/         # Web UI assets
│   ├── templates/      # Flask templates
│   ├── uploads/        # Video storage
│   └── frames/         # Converted frames
├── headless/           # Headless deployment
│   ├── main.py         # Headless player
│   └── videos/         # Video storage
├── display.py          # Shared LCD display handler
├── deploy.sh           # Deployment script
├── tv.local.service    # Systemd service for web interface
└── lib/                # LCD driver
```

## Development

If you want to modify the code:

1. **Setup Dev Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run in Dev Mode**

   ```bash
   # Web mode:
   python web/app.py

   # Headless mode:
   python headless/main.py
   ```

3. **Build Binary**

   ```bash
   # Web mode:
   ./deploy.sh

   # Headless mode:
   ./deploy.sh --headless
   ```

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

## System Optimization

Optional tweaks for better performance:

```bash
# Disable unused services
sudo systemctl disable --now bluetooth

# Reduce GPU memory (headless)
sudo raspi-config nonint do_memory_split 16

# Disable HDMI
echo "hdmi_ignore_hotplug=1" | sudo tee -a /boot/config.txt
```

## Future Plans

- 📡 AP fallback mode
- 🖼️ GIF support
- 🗑️ Web UI file management
- 📊 Performance monitoring

## Contributing

Pull requests welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - See LICENSE file for details
