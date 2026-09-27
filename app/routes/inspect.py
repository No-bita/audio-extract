from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas import InspectRequest, InspectResponse
from app.services.jobs import JobService
from audio_engine.downloader import Downloader
from audio_engine.errors import AudioEngineError


router = APIRouter(prefix="/api", tags=["Inspection"])


def get_job_service(request: Request) -> JobService:
    return request.app.state.job_service


@router.post("/inspect", response_model=InspectResponse)
def inspect_video(req: InspectRequest, service: JobService = Depends(get_job_service)):
    """Inspects YouTube video metadata without downloading any media content."""
    try:
        metadata = Downloader.inspect(req.url)
        service.register_metadata(metadata)
        return InspectResponse(
            source_id=metadata.source_id,
            video_id=metadata.video_id,
            title=metadata.title,
            channel=metadata.channel,
            duration=metadata.duration,
            duration_formatted=metadata.duration_formatted,
            thumbnail_url=metadata.thumbnail_url,
            url=metadata.url,
        )
    except AudioEngineError as e:
        raise HTTPException(status_code=400, detail=e.user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
