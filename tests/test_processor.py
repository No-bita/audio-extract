import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from audio_engine.errors import ProcessingError
from audio_engine.processor import AudioProcessor


@patch("audio_engine.processor.shutil.which", return_value="/usr/local/bin/ffmpeg")
@patch("audio_engine.processor.subprocess.run")
@patch("audio_engine.processor.os.path.exists", return_value=True)
@patch("audio_engine.processor.os.path.getsize", return_value=1024)
def test_convert_full_audio_command(mock_size, mock_exists, mock_run, mock_which, tmp_path):
    source_file = tmp_path / "source.webm"
    output_file = tmp_path / "output.mp3"

    AudioProcessor.convert_full_audio(str(source_file), str(output_file))

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd == [
        "ffmpeg",
        "-y",
        "-i", str(source_file),
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        str(output_file),
    ]


@patch("audio_engine.processor.shutil.which", return_value="/usr/local/bin/ffmpeg")
@patch("audio_engine.processor.subprocess.run")
@patch("audio_engine.processor.os.path.exists", return_value=True)
@patch("audio_engine.processor.os.path.getsize", return_value=1024)
@patch("audio_engine.processor.Inspector.get_duration", return_value=30.05)
def test_trim_audio_command(mock_duration, mock_size, mock_exists, mock_run, mock_which, tmp_path):
    source_file = tmp_path / "source.webm"
    output_file = tmp_path / "output.mp3"

    AudioProcessor.trim_audio(
        source_path=str(source_file),
        start_sec=10.5,
        end_sec=40.5,
        output_path=str(output_file),
    )

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd == [
        "ffmpeg",
        "-y",
        "-ss", "10.500",
        "-t", "30.000",
        "-i", str(source_file),
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        str(output_file),
    ]


@patch("audio_engine.processor.shutil.which", return_value="/usr/local/bin/ffmpeg")
@patch("audio_engine.processor.subprocess.run")
def test_processor_handles_ffmpeg_error(mock_run, mock_which, tmp_path):
    source_file = tmp_path / "source.webm"
    output_file = tmp_path / "output.mp3"

    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["ffmpeg"],
        stderr="Invalid audio stream",
    )

    with pytest.raises(ProcessingError) as exc_info:
        AudioProcessor.convert_full_audio(str(source_file), str(output_file))

    assert "FFmpeg full audio conversion failed" in str(exc_info.value)
