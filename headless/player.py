#!/usr/bin/env python3
import os
import sys
import time
import logging
import subprocess
from pathlib import Path

# Handle bundled modules when running as binary
if getattr(sys, 'frozen', False):
    # Running as compiled binary
    bundle_dir = sys._MEIPASS
    sys.path.append(bundle_dir)

from display import DisplayPlayer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants matching web version
LAST_VIDEO_FILE = '.last_video'
DEFAULT_VIDEO_FILE = '.default_video'
VIDEO_MARKER_FILE = '.video_marker'
ALLOWED_EXTENSIONS = {'mp4'}

def check_web_service():
    """Check if the web version service is running"""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'tv.local'], 
                              capture_output=True, text=True)
        return result.stdout.strip() == 'active'
    except Exception as e:
        logging.error(f"Error checking web service status: {e}")
        return False

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

def write_video_marker(filename):
    """Writes the currently framed video filename to the marker file."""
    try:
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

class HeadlessPlayer:
    def __init__(self, video_dir='videos', frames_dir='frames'):
        self.video_dir = Path(video_dir)
        self.frames_dir = Path(frames_dir)
        self.frames_dir.mkdir(exist_ok=True)
        self.video_dir.mkdir(exist_ok=True)
        
        # Check if web version is running
        if check_web_service():
            logging.warning("Web version (tv.local) is running. Headless player will not start.")
            raise SystemExit("Web version is running. Please stop tv.local service first.")
        
        # Initialize display
        self.display = DisplayPlayer(None, str(self.frames_dir))
        self.display.start()
        
    def convert_to_frames(self, video_path):
        """Convert video to frames using ffmpeg"""
        try:
            # Clear existing frames
            for frame in self.frames_dir.glob('frame_*.png'):
                frame.unlink()
            
            # Convert video to frames
            cmd = [
                'ffmpeg', '-i', str(video_path),
                '-vf', 'scale=320:240:force_original_aspect_ratio=decrease,pad=320:240:(ow-iw)/2:(oh-ih)/2',
                '-r', '12',
                str(self.frames_dir / 'frame_%d.png')
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Write marker on successful conversion
            write_video_marker(video_path.name)
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"FFmpeg conversion failed: {e.stderr.decode()}")
            return False
        except Exception as e:
            logging.error(f"Error converting video: {e}")
            return False

    def play_video(self, video_path):
        """Play a single video file"""
        if not video_path.exists():
            logging.error(f"Video file not found: {video_path}")
            return False
            
        logging.info(f"Converting {video_path} to frames...")
        if not self.convert_to_frames(video_path):
            return False
            
        # Save as last played video
        _save_state_filename(LAST_VIDEO_FILE, video_path.name)
        logging.info("Playing video...")
        return True

    def run(self):
        """Main loop to check for and play videos"""
        try:
            while True:
                # Get all MP4 files in video directory
                videos = list(self.video_dir.glob('*.mp4'))
                
                if videos:
                    # Check for default video first
                    default_video = _load_state_filename(DEFAULT_VIDEO_FILE)
                    if default_video:
                        default_path = self.video_dir / default_video
                        if default_path.exists():
                            video = default_path
                        else:
                            # Default video not found, use first available
                            video = videos[0]
                    else:
                        # No default set, use first available
                        video = videos[0]
                        
                    logging.info(f"Found video: {video}")
                    self.play_video(video)
                else:
                    logging.info("No videos found in directory. Waiting...")
                    time.sleep(5)
                
        except KeyboardInterrupt:
            logging.info("Shutting down...")
        finally:
            self.display.stop()

if __name__ == '__main__':
    player = HeadlessPlayer()
    player.run() 