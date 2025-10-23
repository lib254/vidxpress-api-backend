import logging
from pathlib import Path
import time
import os

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "downloads"
CLEANUP_INTERVAL = 3600  # 1 hour in seconds

def cleanup_old_files(max_age_seconds: int = CLEANUP_INTERVAL):
    """
    Delete files older than max_age_seconds from the temp directory
    """
    try:
        current_time = time.time()
        deleted_count = 0
        
        for file_path in STORAGE_DIR.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                
                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"Deleted old file: {file_path.name}")
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {str(e)}")
        
        logger.info(f"Cleanup completed. Deleted {deleted_count} files.")
    
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
