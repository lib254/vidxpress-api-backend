import yt_dlp
import logging
from pathlib import Path
import shortuuid
from typing import Dict
import os

logger = logging.getLogger(__name__)

# === Paths ===
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "downloads"
COOKIES_FILE = BASE_DIR / "api/utils/cookies.txt"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# === Allowed domains for security ===
ALLOWED_DOMAINS = [
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "vimeo.com",
    "dailymotion.com",
]

def validate_url(url: str) -> bool:
    """Validate if URL is from an allowed domain."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in ALLOWED_DOMAINS)

def _check_cookies_file():
    """Check if cookies file exists and is valid"""
    if not COOKIES_FILE.exists():
        logger.error(f"Cookies file not found at: {COOKIES_FILE}")
        raise FileNotFoundError(
            f"cookies.txt file is required but not found at {COOKIES_FILE}. "
            "Please export fresh cookies from your browser and add them to the project."
        )
    
    # Check if file is empty
    if os.path.getsize(COOKIES_FILE) == 0:
        logger.error("Cookies file is empty")
        raise ValueError(
            "cookies.txt file is empty. Please export fresh cookies from your browser."
        )
    
    # Read and check for valid cookie format
    with open(COOKIES_FILE, 'r') as f:
        content = f.read()
        if "# Netscape HTTP Cookie File" not in content:
            logger.warning("Cookies file may not be in correct Netscape format")
        
        # Check if there are any non-comment lines
        lines = [line for line in content.split('\n') if line.strip() and not line.startswith('#')]
        if len(lines) == 0:
            raise ValueError("No cookies found in cookies.txt file")
        
        logger.info(f"Found {len(lines)} cookies in cookies.txt")

def _get_ydl_opts(base_opts: dict) -> dict:
    """
    Get yt-dlp options with cookies.
    Validates cookies file before use.
    """
    _check_cookies_file()
    
    opts = {
        **base_opts,
        "cookiefile": str(COOKIES_FILE),
        # Additional options to help with bot detection
        "nocheckcertificate": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    return opts

def get_video_metadata(video_url: str) -> Dict:
    """Extract video metadata using yt-dlp."""
    if not validate_url(video_url):
        raise ValueError(f"Domain not supported. Allowed domains: {', '.join(ALLOWED_DOMAINS)}")
    
    try:
        base_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        
        ydl_opts = _get_ydl_opts(base_opts)
        
        logger.info(f"Extracting metadata from: {video_url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Extract available formats
            formats = {"mp4": [], "audio": []}
            if "formats" in info:
                for fmt in info["formats"]:
                    # Filter valid formats
                    if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none":
                        height = fmt.get("height")
                        if height:
                            formats["mp4"].append(f"{height}p")
                    elif fmt.get("acodec") != "none":
                        ext = fmt.get("ext", "m4a")
                        if ext not in formats["audio"]:
                            formats["audio"].append(ext)

            formats["mp4"] = sorted(list(set(formats["mp4"])), reverse=True)
            formats["audio"] = sorted(list(set(formats["audio"])))

            duration_seconds = info.get("duration", 0)
            duration_str = f"{duration_seconds // 60}:{duration_seconds % 60:02d}" if duration_seconds else "Unknown"
            
            return {
                "title": info.get("title", "Unknown"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": duration_str,
                "formats": formats,
            }

    except FileNotFoundError as e:
        logger.error(f"Cookies file error: {str(e)}")
        raise ValueError(
            "Authentication required. The cookies.txt file is missing or invalid. "
            "Please contact the administrator to update the authentication cookies."
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error extracting metadata: {error_msg}")
        
        # Check if it's a bot detection error
        if "Sign in to confirm you're not a bot" in error_msg:
            raise ValueError(
                "YouTube bot detection triggered. The authentication cookies have expired. "
                "Please export fresh cookies from your browser:\n"
                "1. Login to YouTube in your browser\n"
                "2. Use a cookie exporter extension to export cookies.txt\n"
                "3. Replace the cookies.txt file in the project\n"
                "4. Redeploy the application"
            )
        raise

def download_video(video_url: str, format_type: str = "mp4") -> str:
    """Download video or audio using yt-dlp and return the file path."""
    if not validate_url(video_url):
        raise ValueError(f"Domain not supported. Allowed domains: {', '.join(ALLOWED_DOMAINS)}")
    
    file_id = shortuuid.uuid()
    output_template = str(STORAGE_DIR / f"{file_id}.%(ext)s")

    try:
        base_opts = {
            "outtmpl": output_template,
            "quiet": False,  # Enable output for debugging
            "no_warnings": False,
        }

        # Always download best video for processing
        # We'll convert with FFmpeg later
        base_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        
        ydl_opts = _get_ydl_opts(base_opts)
        
        logger.info(f"Downloading video: {video_url}")
        logger.info(f"Output template: {output_template}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # Find the downloaded file
        downloaded_files = list(STORAGE_DIR.glob(f"{file_id}.*"))
        
        if not downloaded_files:
            logger.error(f"No files found matching pattern: {file_id}.*")
            logger.error(f"Files in storage dir: {list(STORAGE_DIR.glob('*'))}")
            raise FileNotFoundError(f"Downloaded file not found for {file_id}")
        
        downloaded_file = str(downloaded_files[0])
        logger.info(f"Successfully downloaded: {downloaded_file}")
        return downloaded_file
    
    except FileNotFoundError as e:
        logger.error(f"Cookies file error: {str(e)}")
        raise ValueError(
            "Authentication required. The cookies.txt file is missing or invalid."
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error downloading video: {error_msg}")
        
        # Check if it's a bot detection error
        if "Sign in to confirm you're not a bot" in error_msg:
            raise ValueError(
                "YouTube bot detection triggered. The authentication cookies have expired. "
                "Please export fresh cookies and update the cookies.txt file."
            )
        raise