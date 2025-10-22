import subprocess
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)

TEMP_DIR = Path("/tmp/files")

def convert_to_mp3(input_file: str, output_file: str) -> bool:
    """
    Convert video file to MP3 using FFmpeg
    """
    try:
        cmd = [
            "ffmpeg",
            "-i", input_file,
            "-q:a", "0",
            "-map", "a",
            "-y",  # Overwrite output file
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")
        
        logger.info(f"Successfully converted {input_file} to {output_file}")
        return True
    
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg conversion timed out")
        raise RuntimeError("Conversion timed out (max 5 minutes)")
    except Exception as e:
        logger.error(f"Error converting file: {str(e)}")
        raise

def convert_to_mp4(input_file: str, output_file: str, quality: str = "720p") -> bool:
    """
    Convert/re-encode video to MP4 using FFmpeg
    quality: '360p', '720p', '1080p'
    """
    try:
        # Map quality to bitrate
        quality_map = {
            "360p": "1000k",
            "720p": "2500k",
            "1080p": "5000k",
        }
        
        bitrate = quality_map.get(quality, "2500k")
        
        cmd = [
            "ffmpeg",
            "-i", input_file,
            "-b:v", bitrate,
            "-b:a", "128k",
            "-y",  # Overwrite output file
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")
        
        logger.info(f"Successfully converted {input_file} to {output_file}")
        return True
    
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg conversion timed out")
        raise RuntimeError("Conversion timed out (max 10 minutes)")
    except Exception as e:
        logger.error(f"Error converting file: {str(e)}")
        raise

def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"Error getting file size: {str(e)}")
        return 0
