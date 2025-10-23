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
            downloaded_file = None
            output_file = None
            
            try:
                logger.info(f"[{task_id}] Starting conversion for {request.video_url}")
                progress_store[task_id] = {"progress": 5, "status": "downloading"}

                # Step 1: Download video (always download as mp4/best quality)
                # Don't let yt-dlp do the conversion - we'll handle it with FFmpeg
                logger.info(f"[{task_id}] Downloading video...")
                downloaded_file = download_video(request.video_url, format_type="mp4")
                
                if not os.path.exists(downloaded_file):
                    raise FileNotFoundError(f"Download failed - file not found: {downloaded_file}")
                
                logger.info(f"[{task_id}] Downloaded to: {downloaded_file}")
                progress_store[task_id] = {"progress": 50, "status": "downloaded"}

                # Step 2: Validate file size
                file_size = get_file_size(downloaded_file)
                logger.info(f"[{task_id}] File size: {file_size / 1024 / 1024:.2f} MB")
                
                if file_size > MAX_FILE_SIZE:
                    if os.path.exists(downloaded_file):
                        os.remove(downloaded_file)
                    progress_store[task_id] = {
                        "progress": 100, 
                        "status": "error", 
                        "error": f"File exceeds 100MB limit ({file_size / 1024 / 1024:.2f} MB)"
                    }
                    return

                # Step 3: Convert to desired format
                progress_store[task_id] = {"progress": 60, "status": "converting"}
                
                # Generate output filename with correct extension
                file_id = shortuuid.uuid()
                output_file = str(TEMP_DIR / f"{file_id}.{request.format}")
                
                logger.info(f"[{task_id}] Converting to {request.format}: {output_file}")

                if request.format == "mp3":
                    convert_to_mp3(downloaded_file, output_file)
                else:  # mp4
                    # If downloaded file is already mp4 and no quality change needed
                    input_ext = Path(downloaded_file).suffix.lower()
                    if input_ext == ".mp4":
                        # Re-encode with quality settings
                        convert_to_mp4(downloaded_file, output_file, request.quality)
                    else:
                        # Convert other formats to mp4
                        convert_to_mp4(downloaded_file, output_file, request.quality)

                progress_store[task_id] = {"progress": 90, "status": "finalizing"}
                
                # Verify output file was created
                if not os.path.exists(output_file):
                    raise FileNotFoundError(f"Conversion failed - output file not created: {output_file}")

                output_size = get_file_size(output_file)
                logger.info(f"[{task_id}] Output file size: {output_size / 1024 / 1024:.2f} MB")

                # Step 4: Cleanup intermediate file
                if downloaded_file and os.path.exists(downloaded_file) and downloaded_file != output_file:
                    try:
                        os.remove(downloaded_file)
                        logger.info(f"[{task_id}] Removed intermediate file: {downloaded_file}")
                    except Exception as e:
                        logger.warning(f"[{task_id}] Could not remove intermediate file: {str(e)}")

                # Generate download URL
                output_file_id = Path(output_file).stem
                download_url = f"https://api.vidxpress.app/api/download/{output_file_id}"

                progress_store[task_id] = {
                    "progress": 100,
                    "status": "complete",
                    "download_url": download_url,
                    "file_id": output_file_id,
                    "format": request.format,
                    "file_size": output_size,
                }

                logger.info(f"[{task_id}] Conversion complete: {output_file_id}")

            except Exception as e:
                logger.error(f"[{task_id}] Conversion error: {str(e)}", exc_info=True)
                
                # Cleanup on error
                for file in [downloaded_file, output_file]:
                    if file and os.path.exists(file):
                        try:
                            os.remove(file)
                            logger.info(f"[{task_id}] Cleaned up file: {file}")
                        except Exception as cleanup_error:
                            logger.warning(f"[{task_id}] Could not cleanup {file}: {cleanup_error}")
                
                progress_store[task_id] = {
                    "progress": 100, 
                    "status": "error", 
                    "error": str(e)
                }

        # Run the task in background
        background_tasks.add_task(process_video)

        return {"status": "started", "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating conversion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start conversion task")


@router.get("/api/progress/{task_id}")
async def progress_stream(task_id: str):
    """
    Stream real-time progress updates for a specific task ID.
    """
    if task_id not in progress_store:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        try:
            while True:
                data = progress_store.get(task_id, {"progress": 0, "status": "pending"})
                yield f"data: {json.dumps(data)}\n\n"

                # ✅ When complete or error, send final event & exit
                if data.get("status") in ["complete", "error"]:
                    # Send final event one more time before closing
                    yield f"data: {json.dumps(data)}\n\n"
                    break

                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error in progress stream: {str(e)}")
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Important for nginx / Cloudflare
        }
    )
