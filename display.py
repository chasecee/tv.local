import os
import time
import threading
from PIL import Image, ImageDraw, ImageFont
import glob
from flask import current_app

# Import Waveshare library
try:
    from lib import LCD_2inch
    HAS_LCD = True
    print("Waveshare LCD library imported.")
except ImportError:
    print("WARN: Waveshare library (lib/LCD_2inch.py) not found. LCD output disabled.")
    HAS_LCD = False

# Helper function to create a status message image
def create_status_image(width, height, message):
    img = Image.new('RGB', (width, height), "BLACK")
    draw = ImageDraw.Draw(img)
    # Load a font (adjust path and size as needed)
    try:
        # Try loading a default font; replace with a path if you add one
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" 
        if not os.path.exists(font_path):
             # Fallback if that font isn't there (path might differ)
             font_path = None # PIL will use a default bitmap font
        font_size = 20
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except IOError:
        print("WARN: Font file not found. Using default PIL font.")
        font = ImageFont.load_default() # Fallback to default bitmap font
        
    # Calculate text size and position
    # For Pillow 10+ use: bbox = draw.textbbox((0, 0), message, font=font)
    # For older Pillow use: text_width, text_height = draw.textsize(message, font=font)
    # Using textlength for Pillow 10+ compatibility, need bbox for height.
    try:
        bbox = draw.textbbox((0, 0), message, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError: # Fallback for older Pillow versions
        print("WARN: Using older Pillow textsize method. Upgrade Pillow recommended.")
        text_width, text_height = draw.textsize(message, font=font)

    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    draw.text((x, y), message, font=font, fill="WHITE")
    return img

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
                # Store dimensions for status image
                self.width = self.disp.width
                self.height = self.disp.height
                # Optional: Clear display
                self.disp.clear()
                # Set backlight (example uses 50%, range 0-100)
                self.disp.bl_DutyCycle(50)
                self.lcd_available = True
            except Exception as e:
                print(f"Error initializing Waveshare LCD: {e}")
                # Set default dims even if init fails, for safety
                self.width = 320 
                self.height = 240
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

    def show_processing_message(self):
        """Displays a 'Processing...' message on the LCD immediately."""
        if not self.lcd_available or not self.disp:
            return # Don't try if LCD isn't working
            
        try:
            print("Displaying Processing message...")
            processing_img = create_status_image(self.width, self.height, "Processing...")
            # Consider rotating if necessary based on physical orientation vs library rotation
            # processing_img = processing_img.rotate(180)
            self.disp.ShowImage(processing_img)
        except Exception as e:
            print(f"Error displaying processing message: {e}")

    def _playback_loop(self):
        """Main loop that plays frames, pausing if processing is active."""
        print("Starting playback loop...")
        last_processing_state = False # Track changes
        while not self._stop_event.is_set():
            is_processing = False # Default
            try: 
                # Check if video processing is happening in the main Flask app
                is_processing = current_app.config.get('PROCESSING_VIDEO', False)
                if is_processing != last_processing_state:
                    print(f"Playback loop: Processing flag is now {is_processing}")
                    last_processing_state = is_processing
                    
                if is_processing:
                    # print("Processing active, pausing playback loop...")
                    time.sleep(0.5) # Wait and check again
                    continue # Skip frame display for this iteration
            except RuntimeError:
                # print("App context not available yet for config check, waiting...")
                time.sleep(0.1)
                continue
            except Exception as e:
                print(f"Error checking processing flag: {e}")
                time.sleep(1) # Wait longer on unexpected errors
                continue

            # --- Reached here: Not processing, proceed with playback ---
            # print("Playback loop: Processing flag is False, attempting playback.") 
            
            frames = self._get_frames()
            if not frames:
                # print("Playback loop: No frames found, waiting...")
                self.current_frame_path = None
                time.sleep(1) 
                continue

            # print(f"Playback loop: Found {len(frames)} frames. Starting loop.")
            for frame_path in frames:
                if self._stop_event.is_set():
                    break
                
                # print(f"Playback loop: Displaying frame {os.path.basename(frame_path)}")
                start_time = time.monotonic()
                self._display_image(frame_path) # Check for errors inside this call in logs
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
