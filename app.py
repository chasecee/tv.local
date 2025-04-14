from flask import Flask, render_template, request, redirect, url_for, flash # Added flash
import os
import subprocess
import atexit # Import atexit
import shutil # Added for disk usage and frame clearing
from display import DisplayPlayer # Import DisplayPlayer
import logging # Added for better logging
import time # For checking modification times (optional optimization)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
# Secret key is needed for flashing messages
# In a real app, use a proper secret key, not this placeholder
app.secret_key = os.urandom(24) 

UPLOAD_FOLDER = 'uploads'
FRAMES_FOLDER = 'frames'
STATIC_FOLDER = 'static'
LAST_VIDEO_FILE = '.last_video' # File to store the last played video filename
DEFAULT_VIDEO_FILE = '.default_video' # File to store the *chosen* default video
VIDEO_MARKER_FILE = os.path.join(FRAMES_FOLDER, '.video_marker') # Marker for existing frames
ALLOWED_EXTENSIONS = {'mp4'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['FRAMES_FOLDER'] = FRAMES_FOLDER
app.config['STATIC_FOLDER'] = STATIC_FOLDER # Ensure static folder config is set
app.config['CURRENT_VIDEO_FILENAME'] = None # Track active video filename
app.config['PROCESSING_VIDEO'] = False # Flag for conversion status

# Initialize Display Player - PASS THE APP OBJECT
player = DisplayPlayer(app=app, frames_folder=app.config['FRAMES_FOLDER'])

# Ensure necessary folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FRAMES_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# Function to stop the player thread gracefully on exit
def shutdown_player():
    logging.info("--- Flask app exiting, attempting player shutdown... ---")
    player.stop()
    logging.info("--- Player shutdown attempt finished. ---")

atexit.register(shutdown_player)

# --- Functions for persisting video state (last and default) ---
def _save_state_filename(filepath, filename):
    """Helper to save a filename to a given state file."""
    try:
        with open(filepath, 'w') as f:
            f.write(filename)
        logging.info(f"Saved state to {filepath}: {filename}")
    except IOError as e:
        logging.error(f"Error saving state to {filepath}: {e}")

def _load_state_filename(filepath):
    """Helper to load a filename from a given state file."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r') as f:
            filename = f.read().strip()
            return filename if filename else None
    except IOError as e:
        logging.error(f"Error loading state from {filepath}: {e}")
        return None

def save_last_video(filename):
    _save_state_filename(LAST_VIDEO_FILE, filename)

def load_last_video():
    return _load_state_filename(LAST_VIDEO_FILE)

def save_default_video(filename):
    _save_state_filename(DEFAULT_VIDEO_FILE, filename)

def load_default_video():
    return _load_state_filename(DEFAULT_VIDEO_FILE)

# --- New Marker File Functions ---
def write_video_marker(filename):
    """Writes the currently framed video filename to the marker file."""
    try:
        # Ensure frames folder exists before writing marker
        os.makedirs(FRAMES_FOLDER, exist_ok=True)
        with open(VIDEO_MARKER_FILE, 'w') as f:
            f.write(filename)
        logging.info(f"Wrote video marker: {filename}")
    except IOError as e:
        logging.error(f"Error writing video marker: {e}")

def read_video_marker():
    """Reads the video filename from the marker file."""
    if not os.path.exists(VIDEO_MARKER_FILE):
        return None
    try:
        with open(VIDEO_MARKER_FILE, 'r') as f:
            return f.read().strip()
    except IOError as e:
        logging.error(f"Error reading video marker: {e}")
        return None

def remove_video_marker():
    """Removes the video marker file if it exists."""
    if os.path.exists(VIDEO_MARKER_FILE):
        try:
            os.remove(VIDEO_MARKER_FILE)
            logging.info("Removed video marker file.")
        except OSError as e:
            logging.error(f"Error removing video marker file: {e}")
# --- End Marker File Functions ---

# --- Function for disk space ---
def get_disk_usage(path='.'):
    """Returns disk usage statistics for the given path."""
    try:
        usage = shutil.disk_usage(path)
        return {
            'total': usage.total,
            'used': usage.used,
            'free': usage.free,
            'percent_free': round((usage.free / usage.total) * 100, 1) if usage.total > 0 else 0
        }
    except FileNotFoundError:
        logging.error(f"Path not found for disk usage: {path}")
        return None
    except Exception as e:
        logging.error(f"Error getting disk usage: {e}")
        return None
# --- End disk space function ---

# --- Function to clear frames directory ---
def clear_frames_folder(output_folder):
    """Removes all files from the frames directory."""
    logging.info(f"Clearing existing frames in {output_folder}...")
    cleared = True
    if not os.path.isdir(output_folder):
        logging.warning(f"Frames folder does not exist: {output_folder}")
        return True # Nothing to clear

    remove_video_marker() # Remove marker when clearing frames

    for filename in os.listdir(output_folder):
        # Skip the marker file itself if it somehow wasn't deleted yet
        if filename == os.path.basename(VIDEO_MARKER_FILE):
            continue
        file_path = os.path.join(output_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                 shutil.rmtree(file_path) # Remove subdirs if any
        except Exception as e:
            logging.error(f'Failed to delete {file_path}. Reason: {e}')
            cleared = False
    if cleared:
        logging.info(f"Successfully cleared {output_folder}.")
    else:
        logging.error(f"Failed to completely clear {output_folder}.")
    return cleared
# --- End frame clearing function ---

def convert_to_frames(video_path, output_folder):
    # Clear existing frames first
    if not clear_frames_folder(output_folder):
        return False # Stop if clearing failed

    # Ensure output folder exists after clearing (it might have been deleted if empty)
    os.makedirs(output_folder, exist_ok=True)

    # FFmpeg command: scale to 320x240, 15 FPS, output PNG frames
    # Consider adding -vf "scale=320:240:force_original_aspect_ratio=decrease,pad=320:240:(ow-iw)/2:(oh-ih)/2"
    # if maintaining aspect ratio with padding is desired.
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vf', 'scale=320:240', # Pre-scale frames
        '-r', '15',              # Output 15 FPS
        os.path.join(output_folder, 'frame_%04d.png') # Naming convention
    ]

    try:
        logging.info(f"Running FFmpeg: {' '.join(ffmpeg_cmd)}")
        result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        # Don't log potentially huge stdout/stderr unless debugging level is set
        logging.debug("FFmpeg stdout:", result.stdout)
        logging.debug("FFmpeg stderr:", result.stderr)
        logging.info("Frame conversion successful.")
        # Write marker on successful conversion
        source_filename = os.path.basename(video_path)
        write_video_marker(source_filename)
        return True # Indicate success
    except FileNotFoundError:
        logging.error("Error: ffmpeg command not found. Please ensure FFmpeg is installed and in PATH.")
        # TODO: Provide feedback to the user via the web UI
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during frame conversion: {e}")
        logging.error("FFmpeg stderr:", e.stderr)
        # TODO: Provide feedback to the user via the web UI
        return False


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Get the filename of the currently active video
    current_video_filename = app.config.get('CURRENT_VIDEO_FILENAME', 'None')

    # Get list of uploaded mp4 files
    available_videos = sorted([f for f in os.listdir(app.config['UPLOAD_FOLDER']) if allowed_file(f)])

    # Get the currently set default video
    default_video_filename = load_default_video()

    # Get disk usage
    disk_usage = get_disk_usage(app.config['UPLOAD_FOLDER']) # Check usage of uploads dir mount point

    return render_template(
        'index.html',
        current_video=current_video_filename,
        default_video=default_video_filename,
        available_videos=available_videos,
        disk_usage=disk_usage
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = file.filename # In future, consider secure_filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        logging.info(f"File {filename} saved to {filepath}")

        # -- Show processing message and convert --
        app.config['PROCESSING_VIDEO'] = True
        player.show_processing_message()
        success = False # Default to failure
        try:
            logging.info(f"Attempting to convert {filename} to frames...")
            success = convert_to_frames(filepath, app.config['FRAMES_FOLDER'])
        finally:
            app.config['PROCESSING_VIDEO'] = False # Ensure flag is reset
            logging.info("Processing flag set to False.")
        # ------------------------------------------

        if success:
            logging.info(f"Successfully converted {filename} to frames.")
            app.config['CURRENT_VIDEO_FILENAME'] = filename # Update current video
            save_last_video(filename) # Save state on success
            flash(f'Successfully uploaded and processed "{filename}".', 'success')
            # Decide if a newly uploaded video should become the default automatically?
            # Let's require explicit setting via UI for now.
            # if not load_default_video():
            #     save_default_video(filename)
            #     flash('Set as default boot video since none was selected.', 'info')
        else:
            logging.error(f"Failed to convert {filename} to frames.")
            flash(f'File "{filename}" uploaded but failed during conversion. Check logs.', 'error')
            # Cleanup failed upload? Maybe leave it for retry?
            # os.remove(filepath) ?

        return redirect(url_for('index'))
    return redirect(request.url) # Or provide feedback

# Route to switch the active video
@app.route('/switch_video/<filename>', methods=['POST'])
def switch_video(filename):
    requested_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(requested_filepath):
        logging.error(f"Error: Requested video file not found: {requested_filepath}")
        # TODO: Flash error message to user
        return redirect(url_for('index'))

    if not allowed_file(filename):
        logging.error(f"Error: Requested file is not an allowed video type: {filename}")
        # TODO: Flash error message to user
        return redirect(url_for('index'))

    logging.info(f"Switching active video to: {filename}")
    # -- Show processing message and convert --
    app.config['PROCESSING_VIDEO'] = True
    player.show_processing_message()
    success = False # Default to failure
    try:
        success = convert_to_frames(requested_filepath, app.config['FRAMES_FOLDER'])
    finally:
        app.config['PROCESSING_VIDEO'] = False # Ensure flag is reset
        logging.info("Processing flag set to False.")
    # ------------------------------------------

    if success:
        logging.info(f"Successfully converted {filename} to frames for playback.")
        app.config['CURRENT_VIDEO_FILENAME'] = filename # Update current video
        save_last_video(filename) # Save state on success
        flash(f'Switched to "{filename}".', 'success')
    else:
        logging.error(f"Failed to convert {filename} for playback.")
        flash(f'Could not switch to "{filename}", conversion failed.', 'error')

    return redirect(url_for('index'))

# --- New Route: Set Default Video ---
@app.route('/set_default/<filename>', methods=['POST'])
def set_default(filename):
    target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(target_path) or not allowed_file(filename):
        flash(f'Cannot set default: Video "{filename}" not found or invalid.', 'error')
        return redirect(url_for('index'))

    save_default_video(filename)
    flash(f'"{filename}" set as the default video for boot.', 'success')
    return redirect(url_for('index'))
# --- End Set Default Route ---

# --- New Route: Delete Video ---
@app.route('/delete_video/<filename>', methods=['POST'])
def delete_video(filename):
    target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    logging.info(f"Attempting to delete video: {filename} at {target_path}")

    if not os.path.exists(target_path) or not allowed_file(filename):
        flash(f'Cannot delete: Video "{filename}" not found or invalid.', 'error')
        return redirect(url_for('index'))

    try:
        os.remove(target_path)
        logging.info(f"Deleted video file: {target_path}")

        # Check if this was the default video
        if filename == load_default_video():
            save_default_video('') # Clear default
            logging.info(f"Cleared default video setting because {filename} was deleted.")

        # Check if this was the last video
        if filename == load_last_video():
            save_last_video('') # Clear last video
            logging.info(f"Cleared last video setting because {filename} was deleted.")

        # Check if this was the currently loaded video
        if filename == app.config.get('CURRENT_VIDEO_FILENAME'):
            logging.info(f"Deleted video {filename} was the current video. Clearing frames.")
            app.config['CURRENT_VIDEO_FILENAME'] = None
            # Clear frames so the player stops showing the old video
            if not clear_frames_folder(app.config['FRAMES_FOLDER']):
                flash('Video file deleted, but failed to clear display frames. Player might show stale content.', 'warning')
            else:
                 flash(f'Successfully deleted "{filename}" and cleared display.', 'success')
            # No need to explicitly remove marker here, clear_frames_folder does it
        else:
            flash(f'Successfully deleted "{filename}".', 'success')

    except OSError as e:
        logging.error(f"Error deleting file {target_path}: {e}")
        flash(f'Error deleting file "{filename}": {e}', 'error')
    except Exception as e:
        logging.error(f"Unexpected error deleting video {filename}: {e}")
        flash(f'An unexpected error occurred while deleting "{filename}".', 'error')

    return redirect(url_for('index'))
# --- End Delete Route ---

if __name__ == '__main__':
    # --- Load video on startup (Default > Last > None) ---
    video_to_load = None
    video_load_source = "None"

    # 1. Try Default Video
    default_video_filename = load_default_video()
    if default_video_filename:
        logging.info(f"Found default video configured: {default_video_filename}")
        default_video_path = os.path.join(app.config['UPLOAD_FOLDER'], default_video_filename)
        if os.path.exists(default_video_path):
            video_to_load = default_video_filename
            video_load_source = "Default"
        else:
            logging.warning(f"Default video file '{default_video_filename}' not found in uploads. Clearing default setting.")
            save_default_video('') # Clear the invalid setting

    # 2. Try Last Video (if default wasn't found/valid)
    if not video_to_load:
        last_video_filename = load_last_video()
        if last_video_filename:
            logging.info(f"No valid default video. Found last video played: {last_video_filename}")
            last_video_path = os.path.join(app.config['UPLOAD_FOLDER'], last_video_filename)
            if os.path.exists(last_video_path):
                video_to_load = last_video_filename
                video_load_source = "Last"
            else:
                logging.warning(f"Last video file '{last_video_filename}' not found in uploads. Clearing last setting.")
                save_last_video('') # Clear the invalid setting

    # 3. Convert the chosen video (if any)
    if video_to_load:
        logging.info(f"Attempting to load video on startup ({video_load_source}): {video_to_load}")
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_to_load)

        # --- Check if frames already exist and match --- 
        marker_filename = read_video_marker()
        frames_exist = any(fname.startswith('frame_') and fname.endswith('.png') for fname in os.listdir(FRAMES_FOLDER)) 

        if marker_filename == video_to_load and frames_exist:
             logging.info(f"Marker file matches '{video_to_load}' and frames exist. Skipping conversion.")
             app.config['PROCESSING_VIDEO'] = False # Ensure this is false
             app.config['CURRENT_VIDEO_FILENAME'] = video_to_load
             # Player will pick up existing frames
        else:
             if marker_filename != video_to_load:
                 logging.info(f"Marker file ('{marker_filename}') does not match target video ('{video_to_load}'). Will convert.")
             if not frames_exist:
                 logging.info("Frames directory is empty or missing PNG frames. Will convert.")
             
             # --- Proceed with conversion --- 
             app.config['PROCESSING_VIDEO'] = True
             player.show_processing_message() # Show message on LCD early
             success = False
             try:
                 success = convert_to_frames(video_path, app.config['FRAMES_FOLDER'])
             finally:
                 app.config['PROCESSING_VIDEO'] = False # Reset flag

             if success:
                 app.config['CURRENT_VIDEO_FILENAME'] = video_to_load
                 logging.info(f"Successfully converted and loaded frames for {video_to_load} ({video_load_source}) on startup.")
             else:
                 logging.error(f"Failed to convert initial video {video_to_load} ({video_load_source}) on startup.")
                 # Clear the state file that pointed to the bad video
                 if video_load_source == "Default":
                     save_default_video('')
                 elif video_load_source == "Last":
                     save_last_video('')
                 # Also clear the marker if conversion failed
                 remove_video_marker()
    else:
        logging.info("No default or last video found/valid, starting with empty player.")
        # Ensure frames folder is empty if we aren't loading anything
        clear_frames_folder(app.config['FRAMES_FOLDER']) # This also removes the marker
    # --- End load video on startup ---

    # Start the display player thread AFTER potentially loading frames
    player.start()
    # TODO: Add arguments for host/port, debug mode
    # Note: Setting debug=True with threading might cause issues like duplicate thread starts.
    # Consider disabling debug mode or using Flask's development server reloading capabilities carefully.
    logging.info("Starting Flask server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False) # Use port 5000 