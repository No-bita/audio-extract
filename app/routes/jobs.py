import os
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from app.schemas import JobCreateRequest, JobStatusResponse
from app.services.jobs import STAGE_MESSAGES, JobService
from audio_engine.errors import SourceNotFoundError


router = APIRouter(prefix="/api", tags=["Jobs"])


def get_job_service(request: Request) -> JobService:
    return request.app.state.job_service


@router.post("/jobs", response_model=JobStatusResponse)
def create_job(
    req: JobCreateRequest,
    background_tasks: BackgroundTasks,
    service: JobService = Depends(get_job_service),
):
    """Creates a background job to convert full audio or clip audio."""
    try:
        record = service.create_job(
            source_id=req.source_id,
            operation=req.operation,
            start=req.start,
            end=req.end,
        )
        # Schedule the background worker
        background_tasks.add_task(
            service.run_job,
            record.job_id,
            req.start,
            req.end,
        )
        return JobStatusResponse(
            job_id=record.job_id,
            status=record.status,
            stage=record.stage,
            message=STAGE_MESSAGES.get(record.stage, "Queued..."),
        )
    except SourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {e}")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, service: JobService = Depends(get_job_service)):
    """Retrieves current execution status and stage for a job."""
    job = service.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    download_url = f"/api/jobs/{job_id}/download" if job.status == "completed" else None

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        stage=job.stage,
        message=STAGE_MESSAGES.get(job.stage, "Processing..."),
        download_url=download_url,
        error=job.error,
    )


@router.get("/jobs/{job_id}/stream")
def stream_job_output(job_id: str, service: JobService = Depends(get_job_service)):
    """Streams the MP3 artifact inline for in-browser audio preview/playback."""
    job = service.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status != "completed" or not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(status_code=400, detail="Audio file is not ready or has expired.")

    return FileResponse(
        path=job.output_path,
        media_type="audio/mpeg",
    )


@router.get("/jobs/{job_id}/download")
def download_job_output(job_id: str, service: JobService = Depends(get_job_service)):
    """Streams the final MP3 artifact as a direct download attachment."""
    job = service.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status != "completed" or not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(status_code=400, detail="Audio file is not ready or has expired.")

    filename = job.output_filename or "audio.mp3"

    return FileResponse(
        path=job.output_path,
        media_type="audio/mpeg",
        filename=filename,
    )
