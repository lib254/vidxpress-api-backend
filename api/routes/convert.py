from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import logging
from pathlib import Path
import os
import asyncio
import json
import shortuuid

from api.utils.downloader import download_video, validate_url
from api.utils.converter import convert_to_mp3, convert_to_mp4, get_file_size

logger = logging.getLogger(__name__)

router = APIRouter()

TEMP_DIR = Path("/tmp/files")
TEMP_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Simple in-memory progress store
progress_store = {}

class ConvertRequest(BaseModel):
    video_url: str
    format: str  # 'mp3' or 'mp4'
    quality: str = "720p"  # For MP4


@router.post("/api/convert")
async def convert_video(request: ConvertRequest, background_tasks: BackgroundTasks):
    """
    Start video download and conversion task (MP3 or MP4)
    Returns a task_id immediately so the frontend can track progress.
    """
    try:
        if not request.video_url:
            raise HTTPException(status_code=400, detail="video_url is required")

        if request.format not in ["mp3", "mp4"]:
            raise HTTPException(status_code=400, detail="format must be 'mp3' or 'mp4'")

        if not validate_url(request.video_url):
            raise HTTPException(status_code=400, detail="URL domain not supported")

        # Generate unique task ID
        task_id = shortuuid.uuid()
        progress_store[task_id] = {"progress": 0, "status": "starting"}

        async def process_video():
            try:
                logger.info(f"[{task_id}] Downloading {request.video_url}")
                progress_store[task_id] = {"progress": 5, "status": "downloading"}

                # Step 1: Download video
                downloaded_file = download_video(request.video_url, request.format)
                progress_store[task_id] = {"progress": 50, "status": "downloaded"}

                # Step 2: Validate file size
                file_size = get_file_size(downloaded_file)
                if file_size > MAX_FILE_SIZE:
                    os.remove(downloaded_file)
                    progress_store[task_id] = {"progress": 100, "status": "error", "error": "File exceeds 100MB"}
                    return

                # Step 3: Convert to desired format
                output_file = downloaded_file.replace(Path(downloaded_file).suffix, f".{request.format}")
                progress_store[task_id] = {"progress": 70, "status": "converting"}

                if request.format == "mp3":
                    convert_to_mp3(downloaded_file, output_file)
                else:
                    convert_to_mp4(downloaded_file, output_file, request.quality)

                progress_store[task_id] = {"progress": 90, "status": "finalizing"}

                # Step 4: Cleanup
                if downloaded_file != output_file and os.path.exists(downloaded_file):
                    try:
                        os.remove(downloaded_file)
                    except Exception as e:
                        logger.warning(f"Could not remove intermediate file: {str(e)}")

                file_id = Path(output_file).stem
                download_url = f"https://api.vidxpress.app/api/download/{file_id}"

                progress_store[task_id] = {
                    "progress": 100,
                    "status": "complete",
                    "download_url": download_url,
                    "file_id": file_id,
                    "format": request.format,
                }

                logger.info(f"[{task_id}] Conversion complete")

            except Exception as e:
                logger.error(f"[{task_id}] Conversion error: {str(e)}")
                progress_store[task_id] = {"progress": 100, "status": "error", "error": str(e)}

        # Run the task in background
        background_tasks.add_task(process_video)

        return {"status": "started", "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating conversion: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start conversion task")


@router.get("/api/progress/{task_id}")
async def progress_stream(task_id: str):
    """
    Stream real-time progress updates for a specific task ID.
    """
    if task_id not in progress_store:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        while True:
            data = progress_store.get(task_id, {"progress": 0, "status": "pending"})
            yield f"data: {json.dumps(data)}\n\n"

            if data.get("status") in ["complete", "error"]:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
