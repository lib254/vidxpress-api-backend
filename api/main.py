from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import logging
import os
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager

from api.utils.cleanup import cleanup_old_files

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up persistent storage directory
STORAGE_DIR = Path("downloads")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Initialize scheduler
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler.add_job(cleanup_old_files, "interval", minutes=60)
    scheduler.start()
    logger.info("Cleanup scheduler started")
    yield
    # Shutdown
    scheduler.shutdown()
    logger.info("Cleanup scheduler stopped")

app = FastAPI(title="VidXpress API", version="1.0.0", lifespan=lifespan)

# Mount downloads directory for static file serving
from fastapi.staticfiles import StaticFiles
app.mount("/files", StaticFiles(directory="downloads"), name="files")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vid-xpress.netlify.app",  # Production frontend
        "http://localhost:5173",           # Development frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Status endpoint with DMCA disclaimer
@app.get("/api/status")
async def status():
    return {
        "status": "online",
        "version": "1.0.0",
        "disclaimer": "VidXpress API is for personal use only. Users are responsible for respecting copyright and intellectual property rights. Downloading copyrighted content without permission may violate DMCA and local laws."
    }

# Import route handlers
from api.routes.fetch import router as fetch_router
from api.routes.convert import router as convert_router
from api.routes.download import router as download_router

app.include_router(fetch_router)
app.include_router(convert_router)
app.include_router(download_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
