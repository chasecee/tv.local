import os
import time
import threading
from PIL import Image
import glob

# Attempt to import Raspberry Pi-specific libraries
try:
    import RPi.GPIO as GPIO
    import spidev
    from ST7789 import ST7789
    HAS_LCD = True
except ImportError:
    print("WARN: Raspberry Pi specific libraries (RPi.GPIO, spidev, ST7789) not found. LCD output disabled.")
    HAS_LCD = False

class DisplayPlayer:
    def __init__(self, frames_folder='frames', fps=15):
        self.frames_folder = frames_folder
        self.fps = fps
        self.frame_delay = 1.0 / fps
        self._thread = None
        self._stop_event = threading.Event()
        self.current_frame_path = None # Track the currently displayed frame
        self.lcd = None
        self.lcd_available = False

        if HAS_LCD:
            try:
                # --- Configuration for Waveshare 2-inch LCD (ST7789) ---
                # IMPORTANT: Verify these pins against the Waveshare example code (2inch_LCD_test.py)
                #            Common pins: RST=25, DC=9, BL=13, CS=SPI0 CS0 (GPIO 8), Port=0
                self.lcd = ST7789(
                    port=0,             # SPI Port (usually 0)
                    cs=0,               # SPI Chip Select (0 or 1, corresponds to CE0 or CE1 / GPIO 8 or 7)
                    dc=9,               # Data/Command (GPIO 9)
                    rst=25,             # Reset (GPIO 25)
                    backlight=13,       # Backlight (GPIO 13) (Set to None if no backlight control)
                    width=320,          # --- Display Width for 2" Screen ---
                    height=240,         # --- Display Height for 2" Screen ---
                    rotation=270,       # --- Adjust rotation: 0/90/180/270 (270 often needed for landscape) ---
                    spi_speed_hz=40000000 # SPI Speed (can try adjusting if issues)
                )
                # -----------------------------------------------------------
                self.lcd.begin()
                print("ST7789 LCD Initialized Successfully (320x240).")
                self.lcd_available = True
                # Optional: Clear display on init with a black image
                black_img = Image.new('RGB', (self.lcd.width, self.lcd.height), (0, 0, 0))
                self.lcd.display(black_img)
            except Exception as e:
                print(f"Error initializing ST7789 LCD: {e}")
                self.lcd = None
                self.lcd_available = False
        else:
            print("LCD hardware/libraries not available. Skipping LCD initialization.")

    def _get_frames(self):
        """Gets a sorted list of frame image paths."""
        # Use glob to find frame files and sort them numerically
        frame_pattern = os.path.join(self.frames_folder, 'frame_*.png')
        frames = sorted(glob.glob(frame_pattern))
        return frames

    def _display_image(self, image_path):
        """Loads the image, ensures correct size/format, and displays it on the LCD if available."""
        try:
            img = Image.open(image_path)
            
            # Ensure image matches LCD dimensions
            if self.lcd_available and self.lcd and img.size != (self.lcd.width, self.lcd.height):
                # Our FFmpeg command should already produce 320x240 frames,
                # but this handles cases where frame size might be different.
                img = img.resize((self.lcd.width, self.lcd.height))

            self.current_frame_path = image_path
            
            if self.lcd_available and self.lcd:
                # Display on the actual LCD - Ensure image is in RGB format
                self.lcd.display(img.convert("RGB")) 
            else:
                # Optional: Print info when LCD is not available
                # print(f"[No LCD] Displaying: {os.path.basename(image_path)} ({img.size[0]}x{img.size[1]})")
                pass # No LCD output

        except Exception as e:
            print(f"Error loading/displaying frame {image_path}: {e}")
            self.current_frame_path = None

    def _playback_loop(self):
        """Main loop that plays frames."""
        print("Starting playback loop...")
        while not self._stop_event.is_set():
            frames = self._get_frames()
            if not frames:
                # No frames found, wait a bit and check again
                # print("No frames found, waiting...")
                self.current_frame_path = None
                time.sleep(1) 
                continue

            # Loop through frames
            for frame_path in frames:
                if self._stop_event.is_set():
                    break # Exit loop immediately if stop event is set
                
                start_time = time.monotonic()
                self._display_image(frame_path)
                end_time = time.monotonic()
                
                # Calculate time spent and sleep for the remaining frame duration
                elapsed_time = end_time - start_time
                sleep_time = self.frame_delay - elapsed_time
                if sleep_time > 0:
                    time.sleep(sleep_time)
                # else: print(f"Warning: Frame display took too long: {elapsed_time:.3f}s")

            # Optional: Brief pause at the end of the loop before checking for new frames again
            # time.sleep(0.1)

        print("Playback loop stopped.")
        self.current_frame_path = None

    def start(self):
        """Starts the playback thread."""
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._thread.start()
            print("Playback thread started.")
        else:
            print("Playback thread already running.")

    def stop(self):
        """Stops the playback thread gracefully and cleans up LCD."""
        if self._thread and self._thread.is_alive():
            print("Stopping playback thread...")
            self._stop_event.set()
            self._thread.join() # Wait for the thread to finish
            print("Playback thread stopped.")
        self._thread = None
        # Clean up LCD resources if they were initialized
        if self.lcd_available and self.lcd:
             try:
                 # Turn off backlight, clear display, etc. (optional)
                 # self.lcd.set_backlight(False)
                 # black_img = Image.new('RGB', (self.lcd.width, self.lcd.height), (0, 0, 0))
                 # self.lcd.display(black_img)
                 # GPIO.cleanup() # May conflict if other parts of system use GPIO
                 print("LCD resources cleaned up.")
             except Exception as e:
                 print(f"Error during LCD cleanup: {e}")
