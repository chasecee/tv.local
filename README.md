RD: Mini TV Player

Overview:
A self-contained Raspberry Pi Zero 2 W display that plays looping video content on a 2" SPI LCD. Users upload MP4 files via a web UI hosted at http://tv.local/. Videos are automatically converted into frame images for smooth playback.

⸻

Features:
• Wi-Fi enabled (joins known network, no AP mode for now)
• Hostname: tv.local (via Avahi/Bonjour)
• Web UI to:
• Upload MP4 files
• View current video
• Switch between available clips
• Auto convert uploaded MP4 to pre-scaled PNG frames using FFmpeg
• Loop video playback on LCD at 15 FPS
• Uses Python (Flask for UI, PIL for display)

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
    # Note: Installs system-wide python packages PIL and Numpy
    sudo pip3 install Flask spidev
    # Installs Flask & spidev using pip (as Waveshare example does for spidev)
    ```

3.  **Clone the Repository:**

    - Choose a location (e.g., the home directory `/home/pi`).

    ```bash
    cd /home/pi
    git clone https://github.com/chasecee/tv.local.git tv.local
    cd tv.local
    ```

    - **Copy Waveshare Library:** Copy the `lib` directory from the Waveshare example code zip
      (e.g., `LCD_Module_RPI_code/RaspberryPi/python/lib`) into this project's root (`tv.local/lib`).

4.  **Install Python Dependencies:**

    - Dependencies should now be installed via `apt` and `pip3` in Step 2.
    - Verify remaining dependencies from `requirements.txt` (if any - should just be Flask/spidev/numpy/Pillow):

    ```bash
    # No longer using requirements.txt directly for install, but keep it for reference
    # sudo pip3 install -r requirements.txt --break-system-packages # Avoid this if possible!
    ```

5.  **Configure LCD Pins (if needed):**

    - Pin configuration is now handled by the Waveshare library (`lib/lcdconfig.py`)
    - You generally shouldn't need to modify `display.py` for pins.

6.  **Configure and Enable Systemd Service:**

    - Edit the service file: `nano tvplayer.service`
    - **IMPORTANT:** Inside the file, update the `User`, `Group`, and `WorkingDirectory` paths.
    - **CRITICAL:** Ensure the `ExecStart` path uses the **system** Python 3 executable. It should look like:
      `ExecStart=/usr/bin/python3 /home/pi/tv.local/app.py`
      (Check `/usr/bin/python3` with `which python3`. Adjust `/home/pi/tv.local` to your path).
    - Copy the service file to the systemd directory:

    ```bash
    sudo cp tvplayer.service /etc/systemd/system/tvplayer.service
    ```

    - Reload systemd, enable the service to start on boot, and start it now:

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable tvplayer.service
    sudo systemctl start tvplayer.service
    ```

    - Check the status:

    ```bash
    sudo systemctl status tvplayer.service
    ```

    - View logs (press Ctrl+C to exit):

    ```bash
    sudo journalctl -fu tvplayer.service
    ```

7.  **Access the Web UI:**
    - Find your Pi's IP address (`hostname -I`).
    - Open a web browser on another computer on the same network and go to `http://<PI_IP_ADDRESS>` (or `http://tv.local` if Avahi/Bonjour is working).

Updating the Code:

- To get the latest changes from your git repository:
  ```bash
  cd /home/pi/tv.local  # Or your project directory
  git pull
  # You might need to reinstall dependencies if requirements.txt changed
  # sudo pip3 install -r requirements.txt
  sudo systemctl restart tvplayer.service
  ```

8.  **System Optimization (Optional):**
    - For better performance, especially on less powerful Pi models, you can disable unused services and hardware features.
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
      - Run `sudo raspi-config`
      - Navigate to `Display Options` -> `HDMI Headless Resolution` (or similar wording depending on OS version).
      - Choose an option to disable HDMI or set a minimal resolution if disable isn't present.
      - Alternatively, edit `/boot/config.txt` (`sudo nano /boot/config.txt`) and add the line `hdmi_ignore_hotplug=1`. Save and reboot.
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
