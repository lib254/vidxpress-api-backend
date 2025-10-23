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
        # Verify input file exists
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file does not exist: {input_file}")
        
        logger.info(f"Converting {input_file} to MP3: {output_file}")
        
        cmd = [
            "ffmpeg",
            "-i", input_file,
            "-vn",  # No video
            "-acodec", "libmp3lame",  # Use MP3 codec
            "-q:a", "2",  # High quality (0-9, lower is better)
            "-ar", "44100",  # Sample rate
            "-y",  # Overwrite output file
            output_file
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300,
            check=False  # Don't raise exception immediately
        )
        
        if result.returncode != 0:
            # Log full error details
            logger.error(f"FFmpeg command: {' '.join(cmd)}")
            logger.error(f"FFmpeg stdout: {result.stdout}")
            logger.error(f"FFmpeg stderr: {result.stderr}")
            logger.error(f"FFmpeg return code: {result.returncode}")
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")
        
        # Verify output file was created
        if not os.path.exists(output_file):
            raise FileNotFoundError(f"FFmpeg did not create output file: {output_file}")
        
        logger.info(f"Successfully converted to MP3: {output_file}")
        return True
    
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg conversion timed out")
        raise RuntimeError("Conversion timed out (max 5 minutes)")
    except Exception as e:
        logger.error(f"Error converting file: {str(e)}", exc_info=True)
        raise

def convert_to_mp4(input_file: str, output_file: str, quality: str = "720p") -> bool:
    """
    Convert/re-encode video to MP4 using FFmpeg
    quality: '360p', '720p', '1080p'
    """
    try:
        # Verify input file exists
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file does not exist: {input_file}")
        
        logger.info(f"Converting {input_file} to MP4 ({quality}): {output_file}")
        
        # Map quality to scale filter
        scale_map = {
            "360p": "scale=-2:360",
            "720p": "scale=-2:720",
            "1080p": "scale=-2:1080",
        }
        
        scale_filter = scale_map.get(quality, "scale=-2:720")
        
        cmd = [
            "ffmpeg",
            "-i", input_file,
            "-vf", scale_filter,  # Scale video
            "-c:v", "libx264",  # H.264 codec
            "-preset", "fast",  # Encoding speed
            "-crf", "23",  # Quality (18-28, lower is better)
            "-c:a", "aac",  # AAC audio codec
            "-b:a", "128k",  # Audio bitrate
            "-movflags", "+faststart",  # Enable streaming
            "-y",  # Overwrite output file
            output_file
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=600,
            check=False
        )
        
        if result.returncode != 0:
            # Log full error details
            logger.error(f"FFmpeg command: {' '.join(cmd)}")
            logger.error(f"FFmpeg stdout: {result.stdout}")
            logger.error(f"FFmpeg stderr: {result.stderr}")
            logger.error(f"FFmpeg return code: {result.returncode}")
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")
        
        # Verify output file was created
        if not os.path.exists(output_file):
            raise FileNotFoundError(f"FFmpeg did not create output file: {output_file}")
        
        logger.info(f"Successfully converted to MP4: {output_file}")
        return True
    
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg conversion timed out")
        raise RuntimeError("Conversion timed out (max 10 minutes)")
    except Exception as e:
        logger.error(f"Error converting file: {str(e)}", exc_info=True)
        raise

def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return 0
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"Error getting file size: {str(e)}")
        return 0

def probe_file(file_path: str) -> dict:
    """
    Use ffprobe to get file information
    Useful for debugging
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
        else:
            logger.error(f"ffprobe failed: {result.stderr}")
            return {}
    except Exception as e:
        logger.error(f"Error probing file: {str(e)}")
        return {}