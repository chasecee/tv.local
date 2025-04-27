#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import time
import threading
import logging
import sys
from PIL import Image, ImageDraw, ImageFont  # Direct import since it will be bundled
import glob

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import Waveshare library
try:
    from lib import LCD_2inch
    HAS_LCD = True
    logging.info("Waveshare LCD library imported.")
except ImportError:
    logging.warning("Waveshare library (lib/LCD_2inch.py) not found. LCD output disabled.")
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
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if not os.path.exists(font_path):
            logging.warning(f"Font not found at {font_path}, trying default.")
            font_path = None
        font_size = 24  # Slightly larger font
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
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
    def __init__(self, app, frames_folder='frames', fps=None):
        self.app = app
        self.frames_folder = frames_folder
        self.fps = fps or app.config.get('FRAME_RATE', 12)  # Use provided fps or get from app config
        self.frame_delay = 1.0 / self.fps
        self._thread = None
        self._stop_event = threading.Event()
        self.current_frame_path = None
        self.disp = None
        self.lcd_available = False
        self.width = 320 # Default width
        self.height = 240 # Default height

        logging.info(f"DisplayPlayer initialized with frame rate: {self.fps} FPS (frame delay: {self.frame_delay:.3f}s)")

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
                # Set backlight (example uses 80%, range 0-100)
                logging.info("Setting backlight to 80%")
                self.disp.bl_DutyCycle(80)
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

    def show_processing_message(self, progress=None):
        """
        Displays a 'Processing...' message on the LCD with optional progress.
        Args:
            progress: Float between 0 and 1 indicating progress, or None
        """
        if not self.lcd_available or not self.disp:
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
            self.disp.ShowImage(processing_img)
        except Exception as e:
            logging.error(f"Error displaying processing message: {e}")

    def _playback_loop(self):
        """Main loop that plays frames, pausing if processing is active."""
        logging.info("Starting playback loop thread...")
        last_processing_state = False # Track changes
        consecutive_processing_checks = 0
        consecutive_no_frames_found = 0

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
                    # Proceed to frame checking

            except Exception as e:
                logging.error(f"Playback loop: Error checking processing flag: {e}")
                time.sleep(1) # Wait longer on unexpected errors
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
