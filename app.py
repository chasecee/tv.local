from flask import Flask, render_template, request, redirect, url_for
import os
import subprocess
import atexit # Import atexit
from display import DisplayPlayer # Import DisplayPlayer
import logging # Added for better logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
FRAMES_FOLDER = 'frames'
STATIC_FOLDER = 'static'
LAST_VIDEO_FILE = '.last_video' # File to store the last played video filename
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

# --- Functions for persisting the last video ---
def save_last_video(filename):
    """Saves the filename to the persistent store."""
    try:
        with open(LAST_VIDEO_FILE, 'w') as f:
            f.write(filename)
        logging.info(f"Saved last video filename: {filename}")
    except IOError as e:
        logging.error(f"Error saving last video state: {e}")

def load_last_video():
    """Loads the filename from the persistent store."""
    if not os.path.exists(LAST_VIDEO_FILE):
        return None
    try:
        with open(LAST_VIDEO_FILE, 'r') as f:
            filename = f.read().strip()
            return filename if filename else None
    except IOError as e:
        logging.error(f"Error loading last video state: {e}")
        return None
# --- End persistence functions ---


def convert_to_frames(video_path, output_folder):
    # Clear existing frames
    logging.info(f"Clearing existing frames in {output_folder}...")
    for filename in os.listdir(output_folder):
        file_path = os.path.join(output_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            # Add elif os.path.isdir(file_path): shutil.rmtree(file_path) if needed
        except Exception as e:
            logging.error(f'Failed to delete {file_path}. Reason: {e}')
            return False # Indicate failure

    # Ensure output folder exists after clearing
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
    available_videos = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if allowed_file(f)]

    return render_template('index.html', current_video=current_video_filename, available_videos=available_videos)

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
        else:
            logging.error(f"Failed to convert {filename} to frames.")
            # TODO: Provide feedback to user on failure

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
    else:
        logging.error(f"Failed to convert {filename} for playback.")
        # TODO: Provide feedback to user on failure

    return redirect(url_for('index'))

# TODO: Add video playback logic (maybe separate module) - DONE via DisplayPlayer

if __name__ == '__main__':
    # --- Load last video on startup ---
    initial_video_filename = load_last_video()
    if initial_video_filename:
        logging.info(f"Found last video played: {initial_video_filename}")
        initial_video_path = os.path.join(app.config['UPLOAD_FOLDER'], initial_video_filename)
        if os.path.exists(initial_video_path):
            logging.info(f"Video file exists: {initial_video_path}. Converting to frames...")
            # Convert frames *before* starting the player thread
            # Set processing flag temporarily (though nothing should be watching yet)
            app.config['PROCESSING_VIDEO'] = True
            player.show_processing_message() # Show message on LCD early
            success = False
            try:
                success = convert_to_frames(initial_video_path, app.config['FRAMES_FOLDER'])
            finally:
                app.config['PROCESSING_VIDEO'] = False # Reset flag

            if success:
                app.config['CURRENT_VIDEO_FILENAME'] = initial_video_filename
                logging.info(f"Pre-loaded frames for {initial_video_filename}")
            else:
                logging.error(f"Failed to convert initial video {initial_video_filename} on startup.")
                # Optionally clear the last video file if conversion fails?
                # save_last_video('')
        else:
            logging.warning(f"Last video file {initial_video_filename} not found in uploads folder. Clearing state.")
            save_last_video('') # Clear the state if the file is missing
    else:
        logging.info("No last video file found, starting with empty player.")
    # --- End load last video ---


    # Start the display player thread AFTER potentially loading frames
    player.start()
    # TODO: Add arguments for host/port, debug mode
    # Note: Setting debug=True with threading might cause issues like duplicate thread starts.
    # Consider disabling debug mode or using Flask's development server reloading capabilities carefully.
    logging.info("Starting Flask server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False) # Use port 5000 