from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from api.utils.downloader import get_video_metadata

logger = logging.getLogger(__name__)

router = APIRouter()

class FetchRequest(BaseModel):
    video_url: str

@router.post("/api/fetch")
async def fetch_metadata(request: FetchRequest):
    """
    Extract video metadata from supported platforms
    """
    try:
        if not request.video_url:
            raise HTTPException(status_code=400, detail="video_url is required")
        
        metadata = get_video_metadata(request.video_url)
        return metadata
    
    except ValueError as e:
        logger.warning(f"Invalid URL: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching metadata: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch metadata")
