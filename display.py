import os
import time
import threading
from PIL import Image, ImageDraw, ImageFont
import glob
import logging

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
             logging.warning(f"Font not found at {font_path}, trying default.")
             font_path = None # PIL will use a default bitmap font
        font_size = 20
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except IOError:
        logging.warning("Font file not found. Using default PIL font.")
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
        logging.warning("Using older Pillow textsize method. Upgrade Pillow recommended.")
        text_width, text_height = draw.textsize(message, font=font)

    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    draw.text((x, y), message, font=font, fill="WHITE")
    return img

class DisplayPlayer:
    def __init__(self, app, frames_folder='frames', fps=15):
        self.app = app
        self.frames_folder = frames_folder
        self.fps = fps
        self.frame_delay = 1.0 / fps
        self._thread = None
        self._stop_event = threading.Event()
        self.current_frame_path = None
        self.disp = None
        self.lcd_available = False
        self.width = 320 # Default width
        self.height = 240 # Default height

        # --- Frame Buffer Attributes ---
        self.buffer_size = 15 # How many frames to load into RAM at once
        self.frame_buffer = [] # Holds pre-loaded PIL Image objects
        self.buffer_index = 0 # Current position within the frame_buffer
        self.current_frame_paths = [] # List of paths for the video being played
        self.path_index = 0 # Current position within current_frame_paths for loading
        # --- End Frame Buffer Attributes ---

        if HAS_LCD:
            try:
                # Initialize Waveshare display object
                # Configuration (pins, etc.) is likely handled inside LCD_2inch based on lcdconfig.py
                self.disp = LCD_2inch.LCD_2inch()
                logging.info("Waveshare LCD object created.")
                self.disp.Init()
                logging.info("Waveshare LCD Initialized Successfully.")
                # Store dimensions for status image
                self.width = self.disp.width
                self.height = self.disp.height
                # Optional: Clear display
                logging.info("Clearing display...")
                self.disp.clear()
                # Set backlight (example uses 50%, range 0-100)
                logging.info("Setting backlight to 50%")
                self.disp.bl_DutyCycle(50)
                self.lcd_available = True
            except Exception as e:
                logging.error(f"Error initializing Waveshare LCD: {e}")
                # Set default dims even if init fails, for safety
                self.width = 320
                self.height = 240
                self.disp = None
                self.lcd_available = False
        else:
            logging.warning("LCD hardware/library not available. Skipping LCD initialization.")

    def _get_frames(self):
        """Gets a sorted list of frame image paths."""
        frame_pattern = os.path.join(self.frames_folder, 'frame_*.png')
        frames = sorted(glob.glob(frame_pattern))
        return frames

    def _display_image_object(self, img_object):
        """Displays a pre-loaded PIL Image object on the LCD."""
        if not self.lcd_available or not self.disp:
            return
        try:
            # Assuming image is already correctly sized/oriented
            # We might clear current_frame_path here or set it differently if needed
            self.disp.ShowImage(img_object)
        except Exception as e:
            logging.error(f"Error displaying image object: {e}")

    def _display_image(self, image_path):
        """Loads the image FROM PATH and displays it on the LCD."""
        if not self.lcd_available or not self.disp:
            return
        try:
            img = Image.open(image_path)
            self.current_frame_path = image_path # Set path when loading this way
            self.disp.ShowImage(img)
        except Exception as e:
            logging.error(f"Error loading/displaying frame {image_path}: {e}")
            self.current_frame_path = None

    def show_processing_message(self):
        """Displays a 'Processing...' message on the LCD immediately."""
        if not self.lcd_available or not self.disp:
            return # Don't try if LCD isn't working
            
        try:
            logging.info("Displaying Processing message...")
            processing_img = create_status_image(self.width, self.height, "Processing...")
            # Consider rotating if necessary based on physical orientation vs library rotation
            # processing_img = processing_img.rotate(180)
            self.disp.ShowImage(processing_img)
        except Exception as e:
            logging.error(f"Error displaying processing message: {e}")

    def _playback_loop(self):
        """Main loop that plays frames, pausing if processing is active."""
        logging.info("Starting playback loop thread...")
        last_processing_state = False # Track changes
        consecutive_processing_checks = 0
        consecutive_no_frames_found = 0

        # Clear buffer state initially
        self.current_frame_paths = []
        self.frame_buffer = []
        self.path_index = 0
        self.buffer_index = 0

        while not self._stop_event.is_set():
            is_processing = False
            try:
                # Check if video processing is happening - USE self.app.config
                is_processing = self.app.config.get('PROCESSING_VIDEO', False)

                if is_processing:
                    if not last_processing_state:
                        logging.info("Playback loop: Detected PROCESSING_VIDEO = True. Pausing playback.")
                        last_processing_state = True
                        consecutive_processing_checks = 0
                    else:
                        consecutive_processing_checks += 1
                        if consecutive_processing_checks % 20 == 0: # Log every 10 seconds (20 * 0.5s sleep)
                            logging.info(f"Playback loop: Still paused due to PROCESSING_VIDEO flag ({consecutive_processing_checks * 0.5:.1f}s).")

                    time.sleep(0.5) # Wait and check again
                    continue # Skip frame display for this iteration
                else:
                    if last_processing_state:
                        logging.info("Playback loop: Detected PROCESSING_VIDEO = False. Resuming playback checks.")
                        last_processing_state = False
                        consecutive_processing_checks = 0 # Reset counter
                        # --- Force buffer invalidation on resuming --- 
                        logging.info("Invalidating frame buffer due to processing state change.")
                        self.current_frame_paths = [] # Force reload of paths
                        self.frame_buffer = []      # Clear loaded images
                        self.path_index = 0
                        self.buffer_index = 0
                        # --- End buffer invalidation --- 
                    # Proceed to frame checking

            except Exception as e:
                logging.error(f"Playback loop: Error checking processing flag: {e}")
                time.sleep(1) # Wait longer on unexpected errors
                continue

            # --- Get current frame paths --- 
            frame_paths = self._get_frames()

            # --- Handle no frames found --- 
            if not frame_paths:
                self.current_frame_path = None
                # Clear buffer state if frames disappear
                if self.current_frame_paths:
                     logging.info("Playback loop: Frames disappeared. Clearing buffer.")
                     self.current_frame_paths = []
                     self.frame_buffer = []
                     self.path_index = 0
                     self.buffer_index = 0
                
                consecutive_no_frames_found += 1
                if consecutive_no_frames_found == 1 or consecutive_no_frames_found % 10 == 0: # Log first time and then every 10 seconds
                     logging.info(f"Playback loop: No frames found in {self.frames_folder}. Waiting... ({consecutive_no_frames_found} checks)")
                time.sleep(1)
                continue
            else:
                if consecutive_no_frames_found > 0:
                    logging.info(f"Playback loop: Found {len(frame_paths)} frames after waiting. Resuming playback.")
                    consecutive_no_frames_found = 0 # Reset counter
            
            # --- Check if frame paths have changed (new video loaded) --- 
            if frame_paths != self.current_frame_paths:
                logging.info(f"Playback loop: Detected change in frame paths (new video?). Found {len(frame_paths)} frames.")
                self.current_frame_paths = frame_paths
                self.frame_buffer = [] # Invalidate buffer
                self.path_index = 0    # Reset path index
                self.buffer_index = 0  # Reset buffer index
                # If path_index was mid-way, starting new video resets it to 0

            # --- Refill buffer if empty --- 
            if not self.frame_buffer:
                logging.debug(f"Frame buffer empty. Loading next {self.buffer_size} frames starting from path index {self.path_index}.")
                frames_to_load = []
                paths_loaded = 0
                for i in range(self.buffer_size):
                    current_path_idx = (self.path_index + i) % len(self.current_frame_paths)
                    frame_path = self.current_frame_paths[current_path_idx]
                    try:
                        img = Image.open(frame_path)
                        frames_to_load.append(img)
                        paths_loaded += 1
                    except Exception as e:
                        logging.error(f"Error loading frame {frame_path} into buffer: {e}")
                        # Should we skip or stop?
                        # Let's stop loading this chunk if one fails.
                        break 
                
                self.frame_buffer = frames_to_load
                self.buffer_index = 0
                # Advance path index by the number of frames actually loaded
                self.path_index = (self.path_index + paths_loaded) % len(self.current_frame_paths)
                logging.debug(f"Loaded {len(self.frame_buffer)} frames into buffer. Next path index: {self.path_index}")
                
                # Handle case where buffer is *still* empty (e.g., all load attempts failed)
                if not self.frame_buffer:
                    logging.error("Failed to load any frames into buffer. Waiting.")
                    time.sleep(1)
                    continue

            # --- Display frame from buffer --- 
            start_time = time.monotonic()
            try:
                img_to_display = self.frame_buffer[self.buffer_index]
                # logging.debug(f"Displaying frame from buffer index {self.buffer_index}")
                self._display_image_object(img_to_display)
                self.buffer_index += 1
            except IndexError:
                # This shouldn't happen if buffer loading logic is correct, but safety first
                logging.warning("Buffer index out of range. Clearing buffer.")
                self.frame_buffer = []
                self.buffer_index = 0
                continue # Skip sleep, try reloading buffer immediately
            except Exception as e:
                 logging.error(f"Unexpected error displaying frame from buffer: {e}")
                 # Maybe clear buffer? Let's try continuing for now.
                 self.buffer_index += 1 # Still advance index

            end_time = time.monotonic()

            # --- Handle buffer exhaustion --- 
            if self.buffer_index >= len(self.frame_buffer):
                logging.debug("Frame buffer exhausted. Will reload on next iteration.")
                self.frame_buffer = [] # Clear buffer
                self.buffer_index = 0 # Reset buffer index (though clearing buffer makes it moot)
                # Path index already advanced during loading
            
            # --- Timing & Sleep --- 
            elapsed_time = end_time - start_time
            sleep_time = self.frame_delay - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)
            #else:
            #    logging.warning(f"Playback loop: Frame display/logic took too long ({elapsed_time:.3f}s), skipping sleep.")

            if self._stop_event.is_set():
                 logging.info("Playback loop: Stop event detected after frame processing.")
                 break # Exit outer loop

        # --- End of while loop --- 
        logging.info("Playback loop thread finished.")
        self.current_frame_path = None

    def start(self):
        """Starts the playback thread."""
        if self._thread is None or not self._thread.is_alive():
            if not self.lcd_available:
                logging.warning("LCD not available, playback thread will not display images.")
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._thread.start()
            logging.info("Playback thread started.")
        else:
            logging.info("Playback thread already running.")

    def stop(self):
        """Stops the playback thread gracefully and cleans up LCD."""
        if self._thread and self._thread.is_alive():
            logging.info("Stopping playback thread...")
            self._stop_event.set()
            logging.info("Stop event set for playback thread.")
            self._thread.join(timeout=3.0) # Increased timeout slightly
            if self._thread.is_alive():
                logging.warning("WARN: Playback thread did not join cleanly after 3 seconds.")
            else:
                logging.info("Playback thread stopped successfully.")
        else:
            logging.info("Stop called but playback thread not running or already stopped.")

        self._thread = None # Ensure thread object is cleared

        if self.lcd_available and self.disp:
             try:
                 logging.info("Cleaning up LCD resources...")
                 # Explicitly turn off backlight and clear screen first
                 logging.info("Setting backlight to 0...")
                 self.disp.bl_DutyCycle(0)
                 logging.info("Clearing display to black...")
                 black_img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
                 # Make sure ShowImage is available before calling
                 if hasattr(self.disp, 'ShowImage'):
                    self.disp.ShowImage(black_img)
                 else:
                    logging.warning("disp object has no ShowImage method during cleanup?")
                 time.sleep(0.1) # Small delay after commands

                 # Now call the library's exit method if available
                 if hasattr(self.disp, 'module_exit'):
                     logging.info("Calling disp.module_exit()...")
                     self.disp.module_exit()
                     logging.info("LCD resources cleaned up successfully via module_exit.")
                 else:
                     logging.warning("disp object has no module_exit method.")

             except Exception as e:
                 logging.error(f"Error during LCD cleanup: {e}")
        else:
            logging.info("LCD resources not available or already cleaned up.")
