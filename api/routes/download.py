from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from api.utils.downloader import download_video
import os

router = APIRouter(prefix="/api/download", tags=["Download"])

@router.get("/")
async def download_video_route(url: str = Query(...), format: str = "mp4"):
    try:
        file_path = download_video(url, format=format)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(
            file_path,
            media_type="video/mp4",
            filename=os.path.basename(file_path)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
