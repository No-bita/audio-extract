import os
import threading
import uuid
from typing import Dict, Optional

from audio_engine.downloader import Downloader
from audio_engine.errors import (
    AudioEngineError,
    SourceNotFoundError,
)
from audio_engine.models import JobRecord, VideoMetadata
from audio_engine.processor import AudioProcessor
from audio_engine.timestamps import ClipValidator, TimestampParser, TimestampResolver
from audio_engine.workspace import WorkspaceManager


STAGE_MESSAGES = {
    "queued": "Job queued for processing...",
    "downloading": "Downloading audio stream from YouTube...",
    "encoding": "Creating your MP3...",
    "completed": "MP3 ready for download!",
    "failed": "Processing failed.",
}


class JobService:
    """Coordinates job lifecycle, caching, and background execution."""

    def __init__(self, workspace: WorkspaceManager):
        self.workspace = workspace
        self.jobs: Dict[str, JobRecord] = {}
        self.metadata_cache: Dict[str, VideoMetadata] = {}
        self._video_locks: Dict[str, threading.Lock] = {}
        self._lock_registry_lock = threading.Lock()

    def _get_video_lock(self, video_id: str) -> threading.Lock:
        with self._lock_registry_lock:
            if video_id not in self._video_locks:
                self._video_locks[video_id] = threading.Lock()
            return self._video_locks[video_id]

    def register_metadata(self, metadata: VideoMetadata) -> None:
        """Caches video metadata under its canonical source_id."""
        self.metadata_cache[metadata.source_id] = metadata

    def get_metadata(self, source_id: str) -> Optional[VideoMetadata]:
        return self.metadata_cache.get(source_id)

    def create_job(
        self,
        source_id: str,
        operation: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> JobRecord:
        """Creates and registers an in-memory job in queued state."""
        metadata = self.get_metadata(source_id)
        if not metadata:
            raise SourceNotFoundError()

        job_id = f"job_{uuid.uuid4().hex[:8]}"

        record = JobRecord(
            job_id=job_id,
            source_id=source_id,
            operation=operation,  # type: ignore
            status="queued",
            stage="queued",
        )
        self.jobs[job_id] = record
        return record

    def run_job(
        self,
        job_id: str,
        start_spec_str: Optional[str] = None,
        end_spec_str: Optional[str] = None,
    ) -> None:
        """Worker execution running inside FastAPI BackgroundTask."""
        job = self.jobs.get(job_id)
        if not job:
            return

        metadata = self.get_metadata(job.source_id)
        if not metadata:
            job.status = "failed"
            job.stage = "failed"
            job.error = SourceNotFoundError.user_message
            return

        try:
            # 1. Download Stage
            job.status = "processing"
            job.stage = "downloading"

            video_id = metadata.video_id
            lock = self._get_video_lock(video_id)

            with lock:
                cached_source = self.workspace.get_cached_source(video_id)
                if cached_source and os.path.exists(cached_source):
                    source_path = cached_source
                else:
                    source_path = Downloader.download_source(
                        metadata.url,
                        self.workspace.sources_dir,
                        video_id,
                    )

            # 2. Encoding / Processing Stage
            job.stage = "encoding"
            output_path = self.workspace.get_job_output_path(job_id)

            # Sanitize track title for filename
            clean_title = "".join(c for c in metadata.title if c.isalnum() or c in " ._-()").strip() or "audio"
            filename_suffix = " (Clip).mp3" if job.operation == "clip" else ".mp3"
            job.output_filename = f"{clean_title}{filename_suffix}"

            if job.operation == "full":
                AudioProcessor.convert_full_audio(source_path, output_path)
            elif job.operation == "clip":
                if not start_spec_str or not end_spec_str:
                    raise AudioEngineError("Start and end timestamps are required for clipping.")

                start_spec = TimestampParser.parse(start_spec_str)
                end_spec = TimestampParser.parse(end_spec_str)

                start_sec = TimestampResolver.resolve(start_spec, metadata.duration)
                end_sec = TimestampResolver.resolve(end_spec, metadata.duration)

                clip_duration = ClipValidator.validate(start_sec, end_sec, metadata.duration)
                job.start_sec = start_sec
                job.end_sec = end_sec

                AudioProcessor.trim_audio(
                    source_path=source_path,
                    start_sec=start_sec,
                    end_sec=end_sec,
                    output_path=output_path,
                    expected_duration=clip_duration,
                )

            # 3. Completion
            job.status = "completed"
            job.stage = "completed"
            job.output_path = output_path

        except AudioEngineError as e:
            job.status = "failed"
            job.stage = "failed"
            job.error = e.user_message
        except Exception as e:
            job.status = "failed"
            job.stage = "failed"
            job.error = f"An unexpected error occurred: {e}"
