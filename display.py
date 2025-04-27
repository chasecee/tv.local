#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import time
import threading
import logging
import sys
from PIL import Image, ImageDraw, ImageFont  # Direct import since it will be bundled
import glob

# Configure logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import Waveshare library
try:
    # First try to import from compiled binary location
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        lib_path = os.path.join(sys._MEIPASS, 'LIB')
        if os.path.exists(lib_path):
            sys.path.insert(0, lib_path)
            logging.info(f"Added PyInstaller bundle path: {lib_path}")
        else:
            logging.warning(f"PyInstaller bundle path not found: {lib_path}")
    
    from lib import LCD_2inch
    HAS_LCD = True
    logging.info("Waveshare LCD library imported.")
except ImportError as e:
    logging.warning(f"Waveshare library (lib/LCD_2inch.py) not found: {e}")
    HAS_LCD = False

# Helper function to create a status message image
def create_status_image(width, height, message, progress=None, rotate=True):
    """
    Create a status message image with optional progress bar.
    Args:
        width: Image width
        height: Image height
        message: Text to display
        progress: Float between 0 and 1 for progress bar, or None for no bar
        rotate: Whether to rotate the image -90 degrees (counterclockwise)
    """
    # Create image in landscape first, we'll rotate later
    img = Image.new('RGB', (height if rotate else width, width if rotate else height), "BLACK")
    draw = ImageDraw.Draw(img)
    
    try:
        # Try loading a default font
        font_size = 24  # Slightly larger font
        font_paths = [
            os.path.join(sys._MEIPASS, 'fonts', 'Font.ttf') if getattr(sys, 'frozen', False) else None,
            os.path.join(os.path.dirname(__file__), 'python', 'Font', 'Font.ttf'),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        ]
        
        font = None
        for path in font_paths:
            if path and os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, font_size)
                    logging.info(f"Using font: {path}")
                    break
                except Exception as e:
                    logging.warning(f"Failed to load font {path}: {e}")
                    continue
        
        if not font:
            logging.warning("No suitable font found, using default PIL font.")
            font = ImageFont.load_default()
    except IOError:
        logging.warning("Font file not found. Using default PIL font.")
        font = ImageFont.load_default()
    
    # Calculate text position
    try:
        bbox = draw.textbbox((0, 0), message, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        text_width, text_height = draw.textsize(message, font=font)

    # Position text in center
    img_width = img.width
    img_height = img.height
    x = (img_width - text_width) // 2
    y = (img_height - text_height) // 2 - 20  # Move text up to make room for progress bar

    # Draw text
    draw.text((x, y), message, font=font, fill="WHITE")

    # Draw progress bar if provided
    if progress is not None:
        progress = max(0, min(1, progress))  # Clamp between 0 and 1
        bar_width = int(img_width * 0.8)  # 80% of width
        bar_height = 10
        bar_x = (img_width - bar_width) // 2
        bar_y = y + text_height + 20  # Position below text
        
        # Draw bar background
        draw.rectangle(
            [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
            outline="WHITE",
            width=1
        )
        
        # Draw progress
        progress_width = int(bar_width * progress)
        if progress_width > 0:
            draw.rectangle(
                [(bar_x + 2, bar_y + 2), (bar_x + progress_width - 2, bar_y + bar_height - 2)],
                fill="WHITE"
            )

    # Rotate if requested
    if rotate:
        img = img.rotate(-90, expand=True)  # -90 degrees (counterclockwise)
    
    return img

class DisplayPlayer:
    def __init__(self, app, frames_folder='frames', fps=12):
        self.app = app  # Can be None for headless mode
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
        self._processing = False  # Local processing flag for headless mode

        if HAS_LCD:
            try:
                # Initialize Waveshare display object
                self.disp = LCD_2inch.LCD_2inch()
                logging.info("Waveshare LCD object created.")
                self.disp.Init()
                logging.info("Waveshare LCD Initialized Successfully.")
                self.width = self.disp.width
                self.height = self.disp.height
                logging.info("Clearing display...")
                self.disp.clear()
                logging.info("Setting backlight to 80%")
                self.disp.bl_DutyCycle(80)
                self.lcd_available = True
            except Exception as e:
                logging.error(f"Error initializing Waveshare LCD: {e}")
                self.width = 320
                self.height = 240
                self.disp = None
                self.lcd_available = False
        else:
            logging.warning("LCD hardware/library not available. Skipping LCD initialization.")

    def is_processing(self):
        """Check if video processing is active, works in both web and headless modes"""
        if self.app:
            # Web mode - use Flask app config
            return self.app.config.get('PROCESSING_VIDEO', False)
        else:
            # Headless mode - use local flag
            return self._processing

    def set_processing(self, state):
        """Set processing state, works in both web and headless modes"""
        if self.app:
            # Web mode - use Flask app config
            self.app.config['PROCESSING_VIDEO'] = state
        else:
            # Headless mode - use local flag
            self._processing = state

    def _get_frames(self):
        """Gets a sorted list of frame image paths."""
        frame_pattern = os.path.join(self.frames_folder, 'frame_*.png')
        frames = sorted(glob.glob(frame_pattern))
        return frames

    def _display_image(self, image_path):
        """Loads the image FROM PATH and displays it on the LCD."""
        if not self.lcd_available or not self.disp:
            logging.warning("LCD not available, skipping image display")
            return
            
        try:
            if not os.path.exists(image_path):
                logging.error(f"Image file not found: {image_path}")
                return
                
            img = Image.open(image_path)
            if not img:
                logging.error(f"Failed to open image: {image_path}")
                return
                
            self.current_frame_path = image_path
            self.disp.ShowImage(img)
            logging.debug(f"Displayed image: {image_path}")
        except Exception as e:
            logging.error(f"Error loading/displaying frame {image_path}: {e}")
            self.current_frame_path = None

    def show_processing_message(self, progress=None):
        """
        Displays a 'Processing...' message on the LCD with optional progress.
        Args:
            progress: Float between 0 and 1 indicating progress, or None
        """
        if not self.lcd_available or not self.disp:
            logging.warning("LCD not available, skipping processing message")
            return
        
        try:
            logging.info(f"Displaying Processing message... Progress: {progress:.1%}" if progress is not None else "Displaying Processing message...")
            processing_img = create_status_image(
                self.width, 
                self.height, 
                "Processing...", 
                progress=progress,
                rotate=True
            )
            if not processing_img:
                logging.error("Failed to create processing image")
                return
                
            self.disp.ShowImage(processing_img)
            logging.debug("Processing message displayed successfully")
        except Exception as e:
            logging.error(f"Error displaying processing message: {e}")

    def _playback_loop(self):
        """Main loop that plays frames, pausing if processing is active."""
        logging.info("Starting playback loop thread...")
        last_processing_state = False
        consecutive_processing_checks = 0
        consecutive_no_frames_found = 0

        while not self._stop_event.is_set():
            try:
                # Use the new is_processing method
                is_processing = self.is_processing()

                if is_processing:
                    if not last_processing_state:
                        logging.info("Playback loop: Processing detected. Pausing playback.")
                        last_processing_state = True
                        consecutive_processing_checks = 0
                    else:
                        consecutive_processing_checks += 1
                        if consecutive_processing_checks % 20 == 0:
                            logging.info(f"Playback loop: Still paused due to processing ({consecutive_processing_checks * 0.5:.1f}s).")

                    time.sleep(0.5)
                    continue

                if last_processing_state:
                    logging.info("Playback loop: Processing finished. Resuming playback checks.")
                    last_processing_state = False
                    consecutive_processing_checks = 0

            except Exception as e:
                logging.error(f"Playback loop: Error checking processing flag: {e}")
                time.sleep(1)
                continue

            # --- Get current frame paths --- 
            frames = self._get_frames()

            # --- Handle no frames found --- 
            if not frames:
                self.current_frame_path = None
                consecutive_no_frames_found += 1
                if consecutive_no_frames_found == 1 or consecutive_no_frames_found % 10 == 0: # Log first time and then every 10 seconds
                     logging.info(f"Playback loop: No frames found in {self.frames_folder}. Waiting... ({consecutive_no_frames_found} checks)")
                time.sleep(1)
                continue
            else:
                if consecutive_no_frames_found > 0:
                    logging.info(f"Playback loop: Found {len(frames)} frames after waiting. Resuming playback.")
                    consecutive_no_frames_found = 0 # Reset counter
            
            # --- Loop through and display frames --- 
            for frame_path in frames:
                if self._stop_event.is_set():
                    logging.info("Playback loop: Stop event detected during frame iteration.")
                    break # Exit inner loop

                # Before displaying, check processing flag *again* using self.app.config
                try:
                    if self.app.config.get('PROCESSING_VIDEO', False):
                         logging.info("Playback loop: Processing started mid-frame-cycle. Breaking cycle.")
                         last_processing_state = True # Set flag to indicate pausing
                         break # Exit inner loop to re-evaluate processing state
                except Exception as e:
                     logging.error(f"Playback loop: Error checking processing flag mid-cycle: {e}")
                     # Decide whether to break or continue
                     break # Safer to break and re-evaluate

                # logging.debug(f"Playback loop: Displaying frame {os.path.basename(frame_path)}")
                start_time = time.monotonic()
                self._display_image(frame_path) # Display the frame
                end_time = time.monotonic()

                # --- Timing & Sleep --- 
                elapsed_time = end_time - start_time
                sleep_time = self.frame_delay - elapsed_time
                if sleep_time > 0:
                    time.sleep(sleep_time)
                #else:
                #    logging.warning(f"Playback loop: Frame display/logic took too long ({elapsed_time:.3f}s), skipping sleep.")

            if self._stop_event.is_set():
                 logging.info("Playback loop: Stop event detected after frame loop.")
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
