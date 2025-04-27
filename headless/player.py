#!/usr/bin/env python3
import os
import time
import logging
import subprocess
from pathlib import Path
from display import DisplayPlayer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HeadlessPlayer:
    def __init__(self, video_dir='videos', frames_dir='frames'):
        self.video_dir = Path(video_dir)
        self.frames_dir = Path(frames_dir)
        self.frames_dir.mkdir(exist_ok=True)
        self.video_dir.mkdir(exist_ok=True)
        
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
            
        logging.info("Playing video...")
        return True

    def run(self):
        """Main loop to check for and play videos"""
        try:
            while True:
                # Get all MP4 files in video directory
                videos = list(self.video_dir.glob('*.mp4'))
                
                if videos:
                    # Play the first video found
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