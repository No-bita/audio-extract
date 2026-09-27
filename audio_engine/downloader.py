import os
import re
from urllib.parse import parse_qs, urlparse
from typing import Optional, Tuple

import yt_dlp

from audio_engine.errors import (
    InvalidURLError,
    MetadataExtractionError,
    PlaylistNotAllowedError,
    VideoUnavailableError,
    DownloadError,
)
from audio_engine.models import VideoMetadata


YOUTUBE_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

VIDEO_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def normalize_youtube_url(raw_url: str) -> Tuple[str, str]:
    """
    Validates and normalizes YouTube URLs into (video_id, canonical_url).
    Strips playlist parameters and rejects pure playlist URLs.
    """
    raw_url = raw_url.strip()
    if not raw_url:
        raise InvalidURLError("URL cannot be empty.")

    # Add scheme if missing
    if not raw_url.startswith(("http://", "https://")):
        raw_url = "https://" + raw_url

    try:
        parsed = urlparse(raw_url)
    except Exception as e:
        raise InvalidURLError(f"Malformed URL: {e}")

    hostname = (parsed.hostname or "").lower()
    if hostname not in YOUTUBE_DOMAINS:
        raise InvalidURLError("Not a valid YouTube URL.")

    path = parsed.path
    query_params = parse_qs(parsed.query)

    video_id: Optional[str] = None

    if hostname in ("youtu.be", "www.youtu.be"):
        # Format: youtu.be/<video_id>
        parts = [p for p in path.split("/") if p]
        if parts:
            video_id = parts[0]
    elif "/shorts/" in path:
        # Format: youtube.com/shorts/<video_id>
        parts = [p for p in path.split("/") if p]
        idx = parts.index("shorts") if "shorts" in parts else -1
        if idx != -1 and idx + 1 < len(parts):
            video_id = parts[idx + 1]
    elif "/watch" in path:
        # Format: youtube.com/watch?v=<video_id>
        v_list = query_params.get("v")
        if v_list and v_list[0]:
            video_id = v_list[0]
        elif "list" in query_params:
            raise PlaylistNotAllowedError()
    elif "/playlist" in path or ("list" in query_params and "v" not in query_params):
        raise PlaylistNotAllowedError()

    if not video_id or not VIDEO_ID_REGEX.match(video_id):
        raise InvalidURLError("Could not identify a valid 11-character YouTube video ID.")

    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    return video_id, canonical_url


def format_duration(seconds: float) -> str:
    """Formats seconds into MM:SS or HH:MM:SS."""
    total_sec = max(0, int(round(seconds)))
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class Downloader:
    """Handles YouTube metadata inspection and raw audio stream acquisition."""

    @staticmethod
    def inspect(raw_url: str) -> VideoMetadata:
        """
        Inspects video metadata without downloading any media content.
        Fast and network-lightweight.
        """
        video_id, canonical_url = normalize_youtube_url(raw_url)

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extract_flat": False,
            "skip_download": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["web", "mweb", "android", "ios"]
                }
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(canonical_url, download=False)
                if not info:
                    raise MetadataExtractionError("No metadata returned by YouTube.")

                duration = float(info.get("duration") or 0.0)
                title = str(info.get("title") or "Untitled Video")
                channel = str(info.get("uploader") or info.get("channel") or "Unknown Channel")
                thumbnail = str(info.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg")

                return VideoMetadata(
                    video_id=video_id,
                    source_id=f"yt_{video_id}",
                    title=title,
                    channel=channel,
                    duration=duration,
                    duration_formatted=format_duration(duration),
                    thumbnail_url=thumbnail,
                    url=canonical_url,
                )

        except yt_dlp.utils.DownloadError as e:
            err_msg = str(e).lower()
            if any(k in err_msg for k in ["private", "unavailable", "sign in", "restricted", "blocked", "not available"]):
                raise VideoUnavailableError(f"Video unavailable: {e}")
            raise MetadataExtractionError(f"Failed to extract metadata: {e}")
        except (InvalidURLError, PlaylistNotAllowedError):
            raise
        except Exception as e:
            raise MetadataExtractionError(f"Unexpected inspection error: {e}")

    @staticmethod
    def download_source(canonical_url: str, output_dir: str, video_id: str) -> str:
        """
        Downloads best available native audio stream without transcoding.
        Returns the absolute filepath to the downloaded source file.
        """
        os.makedirs(output_dir, exist_ok=True)
        outtmpl = os.path.join(output_dir, f"{video_id}.%(ext)s")

        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["web", "mweb", "android", "ios"]
                }
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(canonical_url, download=True)
                downloaded_file = ydl.prepare_filename(info)

                # yt-dlp prepare_filename returns expected path; verify existence
                if not os.path.exists(downloaded_file):
                    # Search output_dir for matching video_id file
                    for fname in os.listdir(output_dir):
                        if fname.startswith(f"{video_id}."):
                            return os.path.join(output_dir, fname)
                    raise DownloadError("Downloaded file could not be found on disk.")

                return downloaded_file

        except yt_dlp.utils.DownloadError as e:
            err_msg = str(e).lower()
            if any(k in err_msg for k in ["private", "unavailable", "sign in", "restricted"]):
                raise VideoUnavailableError(f"Video unavailable: {e}")
            raise DownloadError(f"Download failed: {e}")
        except Exception as e:
            raise DownloadError(f"Unexpected error during audio download: {e}")
