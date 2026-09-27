from dataclasses import dataclass
from typing import Literal, Optional


JobStatus = Literal["queued", "processing", "completed", "failed"]
JobStage = Literal["queued", "downloading", "encoding", "completed", "failed"]
OperationType = Literal["full", "clip"]


@dataclass(frozen=True)
class TimestampSpec:
    """Represents a syntactically parsed timestamp."""
    raw: str
    value_seconds: float
    is_relative_end: bool  # True if starts with '-'


@dataclass(frozen=True)
class VideoMetadata:
    """Metadata retrieved from YouTube without downloading media bytes."""
    video_id: str
    source_id: str  # f"yt_{video_id}"
    title: str
    channel: str
    duration: float  # In seconds
    duration_formatted: str  # MM:SS or HH:MM:SS
    thumbnail_url: str
    url: str


@dataclass
class JobRecord:
    """Internal job state tracking."""
    job_id: str
    source_id: str
    operation: OperationType
    status: JobStatus
    stage: JobStage
    output_path: Optional[str] = None
    output_filename: Optional[str] = None
    error: Optional[str] = None
    start_sec: Optional[float] = None
    end_sec: Optional[float] = None
