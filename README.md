# Mini TV Player

A self-contained video player for Raspberry Pi that displays looping video content on a 2" LCD screen. Features a web UI for video management and compiles to a single binary for maximum reliability.

## Features

- 🎥 Video playback on 2" SPI LCD (320x240)
- 🌐 Web UI at `http://tv.local`
- 📤 Upload and manage MP4 files
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
   ./deploy.sh
   ```

4. **Access**
   - Open `http://tv.local` or `http://<PI_IP_ADDRESS>`
   - Upload an MP4 file
   - Watch it play!

## Binary Deployment Details

The project uses PyInstaller to create a single binary that includes:

- Flask web server
- PIL for image processing
- All Python dependencies
- Static files and templates

Benefits:

- ✨ No Python environment needed
- 🛡️ Resistant to filesystem corruption
- 🚀 Fast startup
- 🔒 Reliable operation

## Project Structure

```
tv.local/
├── app.py              # Main application
├── display.py          # LCD display handler
├── deploy.sh           # Deployment script
├── tv.local.service    # Systemd service for web interface
├── static/             # Web UI assets
├── templates/          # Flask templates
├── uploads/            # Video storage
├── frames/             # Converted frames
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
   python app.py
   ```

3. **Build Binary**
   ```bash
   ./deploy.sh
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
