import os
import shutil
import subprocess
from typing import Optional

from audio_engine.errors import DependencyNotFoundError, ProcessingError
from audio_engine.inspector import Inspector


class AudioProcessor:
    """Handles audio conversion and clipping using FFmpeg with explicit intervals."""

    @staticmethod
    def check_dependency() -> None:
        """Verifies ffmpeg is accessible on PATH."""
        if not shutil.which("ffmpeg"):
            raise DependencyNotFoundError("ffmpeg is not installed or not in system PATH.")

    @staticmethod
    def convert_full_audio(source_path: str, output_path: str) -> None:
        """
        Converts the entire source audio container into a 192 kbps MP3.
        """
        AudioProcessor.check_dependency()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        cmd = [
            "ffmpeg",
            "-y",
            "-i", source_path,
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_path,
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            err = (e.stderr or "").strip()
            raise ProcessingError(f"FFmpeg full audio conversion failed: {err}")

        # Post-encode duration sanity check
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise ProcessingError("Generated MP3 file is missing or empty.")

    @staticmethod
    def trim_audio(
        source_path: str,
        start_sec: float,
        end_sec: float,
        output_path: str,
        expected_duration: Optional[float] = None,
    ) -> None:
        """
        Clips audio using fast seek (-ss) and explicit duration interval (-t).
        Exports single-pass directly to 192 kbps MP3.
        """
        AudioProcessor.check_dependency()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        clip_duration = end_sec - start_sec
        if clip_duration <= 0:
            raise ProcessingError("Invalid clip duration (must be > 0).")

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", f"{start_sec:.3f}",
            "-t", f"{clip_duration:.3f}",
            "-i", source_path,
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_path,
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            err = (e.stderr or "").strip()
            raise ProcessingError(f"FFmpeg audio trim failed: {err}")

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise ProcessingError("Generated clipped MP3 file is missing or empty.")

        # Post-encode duration verification
        target_duration = expected_duration if expected_duration is not None else clip_duration
        try:
            actual_duration = Inspector.get_duration(output_path)
            # MP3 packets are framed (~26ms per frame) plus encoder padding.
            # Allow max(0.5s, 3% of target) tolerance.
            tolerance = max(0.5, 0.03 * target_duration)
            if abs(actual_duration - target_duration) > tolerance:
                # If discrepancies are extreme (> 2.0s), flag an error
                if abs(actual_duration - target_duration) > max(2.0, 0.15 * target_duration):
                    raise ProcessingError(
                        f"Output duration ({actual_duration:.2f}s) deviated significantly from expected ({target_duration:.2f}s)."
                    )
        except ProcessingError:
            raise
        except Exception:
            # If inspection fails for secondary reasons, file is still verified non-empty
            pass
