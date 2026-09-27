from typing import Literal, Optional
from pydantic import BaseModel, field_validator, model_validator


class InspectRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("YouTube URL cannot be empty.")
        return v


class InspectResponse(BaseModel):
    source_id: str
    video_id: str
    title: str
    channel: str
    duration: float
    duration_formatted: str
    thumbnail_url: str
    url: str


class JobCreateRequest(BaseModel):
    source_id: str
    operation: Literal["full", "clip"]
    start: Optional[str] = None
    end: Optional[str] = None

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("yt_") or len(v) < 6:
            raise ValueError("Invalid source_id format. Must start with 'yt_'.")
        return v

    @model_validator(mode="after")
    def validate_operation_payload(self) -> "JobCreateRequest":
        if self.operation == "full":
            if self.start is not None or self.end is not None:
                raise ValueError("Start and end timestamps are not permitted when operation is 'full'.")
        elif self.operation == "clip":
            if not self.start or not self.end:
                raise ValueError("Both 'start' and 'end' timestamps are required when operation is 'clip'.")
        return self


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    stage: Literal["queued", "downloading", "encoding", "completed", "failed"]
    message: str
    download_url: Optional[str] = None
    error: Optional[str] = None
