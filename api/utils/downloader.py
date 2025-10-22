import yt_dlp
import logging
from pathlib import Path
import shortuuid
from typing import Dict

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

def _get_cookie_opts() -> dict:
    """Helper to return cookiefile option if cookies.txt exists."""
    if COOKIES_FILE.exists():
        logger.info(f"Using cookies from {COOKIES_FILE}")
        return {"cookiefile": str(COOKIES_FILE)}
    else:
        logger.warning("No cookies.txt file found — proceeding without authentication.")
        return {}

def get_video_metadata(video_url: str) -> Dict:
    """Extract video metadata using yt-dlp."""
    if not validate_url(video_url):
        raise ValueError(f"Domain not supported. Allowed domains: {', '.join(ALLOWED_DOMAINS)}")
    
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            **_get_cookie_opts(),
        }
        
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
            duration_str = f"{duration_seconds // 60}:{duration_seconds % 60:02d}"
            
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
            **_get_cookie_opts(),
        }

        if format_type == "mp3":
            ydl_opts = {
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
            ydl_opts = {
                **common_opts,
                "format": "bestvideo[ext=mp4]+bestaudio/best[ext=m4a]/mp4",
            }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # Find the downloaded file
        for file in TEMP_DIR.glob(f"{file_id}.*"):
            logger.info(f"Downloaded file: {file}")
            return str(file)
        
        raise FileNotFoundError(f"Downloaded file not found for {file_id}")
    
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        raise
