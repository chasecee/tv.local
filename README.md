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
    sudo apt install -y git ffmpeg python3-pip
    ```

3.  **Clone the Repository:**

    - Choose a location (e.g., the home directory `/home/pi`).

    ```bash
    cd /home/pi
    git clone <YOUR_REPOSITORY_URL> tv.local
    # Replace <YOUR_REPOSITORY_URL> with the actual URL of this git repo
    cd tv.local
    ```

4.  **Install Python Dependencies:**

    ```bash
    sudo pip3 install -r requirements.txt
    ```

5.  **Configure LCD Pins (if needed):**

    - Open `display.py` (`nano display.py`).
    - Verify the pin numbers in the `ST7789(...)` initialization match your hardware wiring and the Waveshare example code (`2inch_LCD_test.py`). Adjust `port`, `cs`, `dc`, `rst`, `backlight`, and `rotation` if necessary.

6.  **Configure and Enable Systemd Service:**

    - Edit the service file: `nano tvplayer.service`
    - **IMPORTANT:** Inside the file, update the `User`, `Group`, `WorkingDirectory`, and `ExecStart` paths to match your username (e.g., `pi`) and the absolute path where you cloned the project (e.g., `/home/pi/tv.local`).
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

⸻

Future:
• AP fallback mode
• GIF support (converted to frames)
• Delete/manage uploads from UI

⸻

You can drop this into a README.md or docs/PRD.md in the new repo. Want a repo structure and base code scaffold next?
