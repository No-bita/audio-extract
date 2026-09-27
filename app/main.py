import os
import shutil
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routes.inspect import router as inspect_router
from app.routes.jobs import router as jobs_router
from app.services.jobs import JobService
from audio_engine.workspace import WorkspaceManager


def check_system_dependencies() -> None:
    """Verifies all required runtime system binaries exist on PATH."""
    missing = []
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if not shutil.which("ffprobe"):
        missing.append("ffprobe")

    if missing:
        msg = (
            f"CRITICAL STARTUP ERROR: Missing required system dependencies: {', '.join(missing)}.\n"
            "Please install them via Homebrew: 'brew install ffmpeg' or your system package manager."
        )
        print(msg, file=sys.stderr)
        raise RuntimeError(msg)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation
    check_system_dependencies()

    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace"))
    workspace = WorkspaceManager(workspace_dir)
    workspace.cleanup_expired()

    app.state.workspace = workspace
    app.state.job_service = JobService(workspace)

    yield

    # Clean temporary files on shutdown
    workspace.cleanup_expired(source_ttl=86400, artifact_ttl=3600)


app = FastAPI(
    title="YouTube Audio Extractor & Clipper",
    description="Clean, user-first tool for extracting full tracks or single contiguous clips from YouTube as MP3.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(inspect_router)
app.include_router(jobs_router)

# Mount Web Assets
web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")


@app.get("/")
def serve_index():
    index_path = os.path.join(web_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(
            index_path,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    return {"message": "YouTube Audio Extractor API is operational."}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "ffprobe": bool(shutil.which("ffprobe")),
    }
