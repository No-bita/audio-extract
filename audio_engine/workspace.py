import os
import shutil
import time
from typing import Optional


SOURCE_TTL_SECONDS = 86400.0   # 24 hours
ARTIFACT_TTL_SECONDS = 3600.0  # 1 hour


class WorkspaceManager:
    """Manages workspace lifecycle, directory structure, source caching, and TTL cleanup."""

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        self.sources_dir = os.path.join(self.root_dir, "sources")
        self.jobs_dir = os.path.join(self.root_dir, "jobs")
        self.temp_dir = os.path.join(self.root_dir, "temp")
        self.ensure_directories()

    def ensure_directories(self) -> None:
        """Ensures all required workspace subdirectories exist."""
        for d in (self.sources_dir, self.jobs_dir, self.temp_dir):
            os.makedirs(d, exist_ok=True)

    def get_cached_source(self, video_id: str) -> Optional[str]:
        """
        Returns filepath if a cached source exists for video_id and has not expired.
        """
        if not os.path.exists(self.sources_dir):
            return None

        for fname in os.listdir(self.sources_dir):
            if fname.startswith(f"{video_id}."):
                fpath = os.path.join(self.sources_dir, fname)
                # Check file existence and non-zero size
                if os.path.isfile(fpath) and os.path.getsize(fpath) > 0:
                    # Update access timestamp for LRU-style retention
                    try:
                        os.utime(fpath, None)
                    except OSError:
                        pass
                    return fpath
        return None

    def get_job_output_path(self, job_id: str) -> str:
        """Returns the target output MP3 path for a job."""
        job_dir = os.path.join(self.jobs_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        return os.path.join(job_dir, "output.mp3")

    def cleanup_expired(
        self,
        source_ttl: float = SOURCE_TTL_SECONDS,
        artifact_ttl: float = ARTIFACT_TTL_SECONDS,
    ) -> None:
        """Purges expired sources and job artifacts."""
        now = time.time()

        # Clean sources older than source_ttl
        if os.path.exists(self.sources_dir):
            for fname in os.listdir(self.sources_dir):
                fpath = os.path.join(self.sources_dir, fname)
                try:
                    if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > source_ttl:
                        os.remove(fpath)
                except OSError:
                    pass

        # Clean job directories older than artifact_ttl
        if os.path.exists(self.jobs_dir):
            for job_id in os.listdir(self.jobs_dir):
                jpath = os.path.join(self.jobs_dir, job_id)
                try:
                    if os.path.isdir(jpath) and (now - os.path.getmtime(jpath)) > artifact_ttl:
                        shutil.rmtree(jpath, ignore_errors=True)
                except OSError:
                    pass

        # Clean temp directory
        if os.path.exists(self.temp_dir):
            for fname in os.listdir(self.temp_dir):
                tpath = os.path.join(self.temp_dir, fname)
                try:
                    if os.path.isfile(tpath):
                        os.remove(tpath)
                    elif os.path.isdir(tpath):
                        shutil.rmtree(tpath, ignore_errors=True)
                except OSError:
                    pass
