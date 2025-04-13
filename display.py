import os
import time
import threading
from PIL import Image
import glob

# Import Waveshare library
try:
    from lib import LCD_2inch
    HAS_LCD = True
    print("Waveshare LCD library imported.")
except ImportError:
    print("WARN: Waveshare library (lib/LCD_2inch.py) not found. LCD output disabled.")
    HAS_LCD = False

class DisplayPlayer:
    def __init__(self, frames_folder='frames', fps=15):
        self.frames_folder = frames_folder
        self.fps = fps
        self.frame_delay = 1.0 / fps
        self._thread = None
        self._stop_event = threading.Event()
        self.current_frame_path = None
        self.disp = None
        self.lcd_available = False

        if HAS_LCD:
            try:
                # Initialize Waveshare display object
                # Configuration (pins, etc.) is likely handled inside LCD_2inch based on lcdconfig.py
                self.disp = LCD_2inch.LCD_2inch()
                print("Waveshare LCD object created.")
                self.disp.Init()
                print("Waveshare LCD Initialized Successfully.")
                # Optional: Clear display
                self.disp.clear()
                # Set backlight (example uses 50%, range 0-100)
                self.disp.bl_DutyCycle(50)
                self.lcd_available = True
            except Exception as e:
                print(f"Error initializing Waveshare LCD: {e}")
                self.disp = None
                self.lcd_available = False
        else:
            print("LCD hardware/library not available. Skipping LCD initialization.")

    def _get_frames(self):
        """Gets a sorted list of frame image paths."""
        frame_pattern = os.path.join(self.frames_folder, 'frame_*.png')
        frames = sorted(glob.glob(frame_pattern))
        return frames

    def _display_image(self, image_path):
        """Loads the image and displays it on the LCD using Waveshare library."""
        if not self.lcd_available or not self.disp:
            # print("[No LCD] Skipping display.")
            return
            
        try:
            img = Image.open(image_path)
            
            # Waveshare example rotates the image by 180 degrees before display
            # We assume the library expects landscape orientation matching the 320 width
            # Check if image is already 320x240 from FFmpeg
            # Note: Waveshare lib might have different width/height attributes than st7789
            # If orientation is wrong, uncommenting the rotate might help.
            # img = img.rotate(180)
            
            self.current_frame_path = image_path
            self.disp.ShowImage(img) 

        except Exception as e:
            print(f"Error loading/displaying frame {image_path}: {e}")
            self.current_frame_path = None

    def _playback_loop(self):
        """Main loop that plays frames."""
        print("Starting playback loop...")
        while not self._stop_event.is_set():
            frames = self._get_frames()
            if not frames:
                self.current_frame_path = None
                time.sleep(1) 
                continue

            for frame_path in frames:
                if self._stop_event.is_set():
                    break
                
                start_time = time.monotonic()
                self._display_image(frame_path)
                end_time = time.monotonic()
                
                elapsed_time = end_time - start_time
                sleep_time = self.frame_delay - elapsed_time
                if sleep_time > 0:
                    time.sleep(sleep_time)

        print("Playback loop stopped.")
        self.current_frame_path = None

    def start(self):
        """Starts the playback thread."""
        if self._thread is None or not self._thread.is_alive():
            if not self.lcd_available:
                print("WARN: LCD not available, playback thread will not display images.")
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
            self._thread.join()
            print("Playback thread stopped.")
        self._thread = None
        
        if self.lcd_available and self.disp:
             try:
                 print("Cleaning up LCD resources...")
                 # Use Waveshare library's exit method
                 self.disp.module_exit()
                 print("LCD resources cleaned up.")
             except Exception as e:
                 print(f"Error during LCD cleanup: {e}")
