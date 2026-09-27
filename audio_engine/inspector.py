import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from audio_engine.errors import DependencyNotFoundError, ProcessingError


@dataclass(frozen=True)
class AudioStreamInfo:
    duration: float
    codec: str
    sample_rate: int
    channels: int


class Inspector:
    """Probes local audio files using ffprobe."""

    @staticmethod
    def check_dependency() -> None:
        """Verifies ffprobe is accessible on PATH."""
        if not shutil.which("ffprobe"):
            raise DependencyNotFoundError("ffprobe is not installed or not in system PATH.")

    @staticmethod
    def get_duration(file_path: str) -> float:
        """Retrieves media duration in seconds via ffprobe."""
        Inspector.check_dependency()
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = res.stdout.strip()
            if not output:
                raise ProcessingError("ffprobe returned empty duration.")
            return float(output)
        except (subprocess.CalledProcessError, ValueError) as e:
            raise ProcessingError(f"ffprobe failed to probe duration of {file_path}: {e}")

    @staticmethod
    def probe_stream(file_path: str) -> AudioStreamInfo:
        """Retrieves detailed audio stream properties."""
        Inspector.check_dependency()
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name,sample_rate,channels:format=duration",
            "-of", "json",
            file_path,
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            format_info = data.get("format", {})
            duration = float(format_info.get("duration", 0.0))

            streams = data.get("streams", [])
            if not streams:
                raise ProcessingError("No audio streams found in file.")

            audio_stream = streams[0]
            codec = str(audio_stream.get("codec_name", "unknown"))
            sample_rate = int(audio_stream.get("sample_rate", 44100))
            channels = int(audio_stream.get("channels", 2))

            return AudioStreamInfo(
                duration=duration,
                codec=codec,
                sample_rate=sample_rate,
                channels=channels,
            )
        except (subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as e:
            raise ProcessingError(f"ffprobe stream inspection failed: {e}")
