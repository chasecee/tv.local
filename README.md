RD: Mini TV Player

Overview:
A self-contained Raspberry Pi Zero 2 W display that plays looping video content on a 2" SPI LCD. Users upload MP4 files via a web UI hosted at http://tv.local/. Videos are automatically converted into frame images for smooth playback. The application can be deployed as a standalone binary for improved reliability and resilience against power loss.

⸻

Features:
• Wi-Fi enabled (joins known network, no AP mode for now)
• Hostname: tv.local (via Avahi/Bonjour)
• Web UI to:
• Upload MP4 files
• View current video
• Switch between available clips
• Auto convert uploaded MP4 to pre-scaled PNG frames using FFmpeg
• Loop video playback on LCD at 12 FPS
• Uses Python (Flask for UI, PIL for display)
• Self-healing PIL installation if corruption occurs

⸻

Tech stack:
• Flask (web server)
• FFmpeg (video → frame conversion)
• Pillow (image display)
• spidev + ST7789 driver (LCD)
• Systemd service for boot playback
• Hostname via avahi-daemon

⸻

Directories:
• /frames/ – active video frame PNGs
• /uploads/ – original MP4s
• /static/ – web UI assets

⸻

Raspberry Pi Setup:

Prerequisites:

- Raspberry Pi (tested on Zero 2 W, should work on others)
- Raspberry Pi OS (Bullseye or later recommended)
- Network connection (Wi-Fi or Ethernet)
- 2" SPI LCD (Waveshare ST7789 320x240 recommended)

Steps:

1.  **Enable SPI:**

    - Run `sudo raspi-config`
    - Navigate to `Interface Options` -> `SPI`
    - Select `<Yes>` to enable the SPI interface.
    - Reboot if prompted.

2.  **Install System Dependencies:**

    ```bash
    sudo apt update
    sudo apt install -y git ffmpeg python3-pip python3-pil python3-numpy libjpeg62-turbo-dev libopenblas-dev
    sudo pip3 install Flask spidev
    ```

3.  **Clone and Install:**

    ```bash
    cd /home/pi
    git clone https://github.com/chasecee/tv.local.git tv.local
    cd tv.local
    sudo ./install.sh
    ```

    - **Copy Waveshare Library:** Copy the `lib` directory from the Waveshare example code zip
      (e.g., `LCD_Module_RPI_code/RaspberryPi/python/lib`) into this project's root (`tv.local/lib`).

4.  **Access the Web UI:**
    - Find your Pi's IP address (`hostname -I`)
    - Open a web browser on another computer on the same network
    - Go to `http://<PI_IP_ADDRESS>` or `http://tv.local` if Avahi/Bonjour is working
    - No port number needed - the web interface runs on standard port 80

Updating the Code:

```bash
cd /home/pi/tv.local
git pull
sudo ./install.sh  # This will update service files and permissions
```

Binary Deployment (Recommended):
For improved reliability, especially in environments with frequent power loss, you can deploy the application as a standalone binary:

1. **Run deploy script:**

   ```bash
   ./deploy.sh
   ```

   This will:

   - Install/update required apt packages (python3-flask, python3-pil, python3-pyinstaller, etc.)
   - Pull latest code
   - Build a fresh binary
   - Stop the service
   - Replace the old binary
   - Restart the service

   The binary deployment is more resilient to power loss and filesystem corruption as it doesn't rely on .pyc files or a complete Python environment.

   Note: All Python dependencies are managed through apt for maximum system stability.

Troubleshooting:

1. **Check Service Status:**

   ```bash
   sudo systemctl status tvplayer
   ```

2. **View Logs:**

   ```bash
   sudo journalctl -fu tvplayer
   ```

3. **Common Issues:**
   - If the web interface isn't accessible, check that the service is running
   - If videos won't upload, check permissions on the uploads directory
   - The system will automatically attempt to repair itself if PIL becomes corrupted

⸻

System Optimization (Optional):

- **Disable Bluetooth:**
  ```bash
  sudo systemctl disable --now bluetooth
  # To re-enable later if needed:
  # sudo systemctl enable --now bluetooth
  ```
- **Boot to Command Line (if running headless):** If you don't need the graphical desktop:
  - Run `sudo raspi-config`
  - Navigate to `System Options` -> `Boot / Auto Login`
  - Select `Console` or `Console (Autologin)`.
  - Reboot when prompted.
- **Adjust GPU Memory (if running headless or minimal graphics):**
  - Run `sudo raspi-config`
  - Navigate to `Performance Options` -> `GPU Memory`
  - Enter a lower value (e.g., `16` or `32` MB). The minimum is usually 16MB. Too low might cause issues if any graphics are still used, but 16/32 is often safe for headless/CLI-only setups.
  - Reboot when prompted.
- **Disable HDMI Output (if not using HDMI):**
  - The location for this option in `sudo raspi-config` can vary between OS versions (e.g., under `Display Options` or similar). Look for settings related to headless operation or HDMI resolution.
  - **Alternatively, and more reliably:** Edit `/boot/config.txt` directly:
    ```bash
    sudo nano /boot/config.txt
    ```
    Add the following line anywhere in the file:
    ```
    hdmi_ignore_hotplug=1
    ```
    Save the file (Ctrl+X, then Y, then Enter) and reboot.
- **Disable Onboard Audio (if not using audio):**
  - Run `sudo raspi-config`
  - Navigate to `System Options` -> `Audio`
  - Select `Force Headphones` or `Force HDMI` (if HDMI is also disabled, this effectively silences it), or look for an explicit `Disable` option if available.
  - Alternatively, edit `/boot/config.txt` (`sudo nano /boot/config.txt`), find the line `dtparam=audio=on` and change it to `dtparam=audio=off`. Save and reboot.
- **Other Considerations:**
  - **Disable Avahi:** If you don't need `.local` hostname resolution and will use the Pi's IP address, you can disable Avahi: `sudo systemctl disable --now avahi-daemon`
  - **Disable WiFi:** If using only Ethernet: `sudo rfkill block wifi` (temporary) or potentially disable via `raspi-config` or `/boot/config.txt` depending on the Pi model and OS version.

⸻

Future:
• AP fallback mode
• GIF support (converted to frames)
• Delete/manage uploads from UI

⸻
