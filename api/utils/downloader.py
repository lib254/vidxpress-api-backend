import yt_dlp
import logging
from pathlib import Path
import shortuuid
from typing import Dict
import time

logger = logging.getLogger(__name__)

# === Paths ===
BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = Path("/tmp/files")
COOKIES_FILE = BASE_DIR / "cookies.txt"

TEMP_DIR.mkdir(parents=True, exist_ok=True)

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

def _get_cookie_strategies() -> list:
    """
    Return a list of cookie strategies to try in order.
    Each strategy is a tuple of (description, yt-dlp options dict)
    """
    strategies = []
    
    # Strategy 1: Use cookies.txt file if it exists
    if COOKIES_FILE.exists():
        strategies.append((
            f"cookies file at {COOKIES_FILE}",
            {"cookiefile": str(COOKIES_FILE)}
        ))
    
    # Strategy 2: Try to extract cookies from browsers
    browsers = ["chrome", "firefox", "edge", "safari", "brave"]
    for browser in browsers:
        strategies.append((
            f"cookies from {browser} browser",
            {"cookiesfrombrowser": (browser,)}
        ))
    
    # Strategy 3: No cookies (last resort)
    strategies.append((
        "no authentication (may fail for some videos)",
        {}
    ))
    
    return strategies

def _try_with_strategies(url: str, base_opts: dict, download: bool = False) -> Dict:
    """
    Try to extract info or download with multiple cookie strategies.
    
    Args:
        url: Video URL
        base_opts: Base yt-dlp options
        download: Whether to download (True) or just extract info (False)
    
    Returns:
        Video info dict or raises exception if all strategies fail
    """
    strategies = _get_cookie_strategies()
    last_error = None
    
    for i, (description, cookie_opts) in enumerate(strategies, 1):
        try:
            logger.info(f"Attempt {i}/{len(strategies)}: Using {description}")
            
            ydl_opts = {**base_opts, **cookie_opts}
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if download:
                    ydl.download([url])
                    return {"success": True}
                else:
                    info = ydl.extract_info(url, download=False)
                    logger.info(f"✓ Successfully extracted metadata using {description}")
                    return info
                    
        except Exception as e:
            error_msg = str(e)
            last_error = error_msg
            
            # Check if it's a bot detection error
            if "Sign in to confirm you're not a bot" in error_msg:
                logger.warning(f"✗ Bot detection with {description}: {error_msg[:100]}")
                # Add a small delay before trying next strategy
                if i < len(strategies):
                    time.sleep(1)
                continue
            elif "ERROR: Unable to extract" in error_msg:
                logger.warning(f"✗ Extraction failed with {description}: {error_msg[:100]}")
                continue
            else:
                # For other errors, might be worth trying other strategies
                logger.error(f"✗ Error with {description}: {error_msg[:150]}")
                if i < len(strategies):
                    continue
    
    # All strategies failed
    error_detail = f"All authentication strategies failed. Last error: {last_error}"
    if "Sign in to confirm you're not a bot" in str(last_error):
        error_detail += "\n\nSUGGESTION: Your cookies may be expired. Please:"
        error_detail += "\n1. Export fresh cookies from your browser using a cookie exporter extension"
        error_detail += "\n2. Replace the cookies.txt file with the fresh export"
        error_detail += "\n3. Make sure you're logged into YouTube in your browser"
    
    raise Exception(error_detail)

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
        
        info = _try_with_strategies(video_url, base_opts, download=False)
        
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

    except Exception as e:
        logger.error(f"Error extracting metadata: {str(e)}")
        raise

def download_video(video_url: str, format_type: str = "mp4") -> str:
    """Download video or audio using yt-dlp and return the file path."""
    if not validate_url(video_url):
        raise ValueError(f"Domain not supported. Allowed domains: {', '.join(ALLOWED_DOMAINS)}")
    
    file_id = shortuuid.uuid()
    output_template = str(TEMP_DIR / f"{file_id}.%(ext)s")

    try:
        common_opts = {
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
        }

        if format_type == "mp3":
            base_opts = {
                **common_opts,
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
        else:  # mp4
            base_opts = {
                **common_opts,
                "format": "bestvideo[ext=mp4]+bestaudio/best[ext=m4a]/mp4",
            }
        
        _try_with_strategies(video_url, base_opts, download=True)
        
        # Find the downloaded file
        for file in TEMP_DIR.glob(f"{file_id}.*"):
            logger.info(f"Downloaded file: {file}")
            return str(file)
        
        raise FileNotFoundError(f"Downloaded file not found for {file_id}")
    
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        raise