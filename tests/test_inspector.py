import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from audio_engine.errors import DependencyNotFoundError, ProcessingError
from audio_engine.inspector import AudioStreamInfo, Inspector


@patch("audio_engine.inspector.shutil.which", return_value=None)
def test_check_dependency_missing(mock_which):
    with pytest.raises(DependencyNotFoundError):
        Inspector.check_dependency()


@patch("audio_engine.inspector.shutil.which", return_value="/usr/local/bin/ffprobe")
@patch("audio_engine.inspector.subprocess.run")
def test_get_duration_success(mock_run, mock_which):
    mock_run.return_value = MagicMock(stdout="142.50\n", returncode=0)
    duration = Inspector.get_duration("/path/to/audio.mp3")
    assert duration == 142.50
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "ffprobe" in cmd
    assert "format=duration" in cmd


@patch("audio_engine.inspector.shutil.which", return_value="/usr/local/bin/ffprobe")
@patch("audio_engine.inspector.subprocess.run")
def test_get_duration_empty_output(mock_run, mock_which):
    mock_run.return_value = MagicMock(stdout="", returncode=0)
    with pytest.raises(ProcessingError):
        Inspector.get_duration("/path/to/audio.mp3")


@patch("audio_engine.inspector.shutil.which", return_value="/usr/local/bin/ffprobe")
@patch("audio_engine.inspector.subprocess.run")
def test_probe_stream_success(mock_run, mock_which):
    probe_data = {
        "format": {"duration": "180.20"},
        "streams": [
            {
                "codec_name": "opus",
                "sample_rate": "48000",
                "channels": 2,
            }
        ],
    }
    mock_run.return_value = MagicMock(stdout=json.dumps(probe_data), returncode=0)

    info = Inspector.probe_stream("/path/to/audio.webm")
    assert isinstance(info, AudioStreamInfo)
    assert info.duration == 180.20
    assert info.codec == "opus"
    assert info.sample_rate == 48000
    assert info.channels == 2


@patch("audio_engine.inspector.shutil.which", return_value="/usr/local/bin/ffprobe")
@patch("audio_engine.inspector.subprocess.run")
def test_probe_stream_no_audio_streams(mock_run, mock_which):
    probe_data = {
        "format": {"duration": "180.20"},
        "streams": [],
    }
    mock_run.return_value = MagicMock(stdout=json.dumps(probe_data), returncode=0)

    with pytest.raises(ProcessingError) as exc_info:
        Inspector.probe_stream("/path/to/video_only.mp4")
    assert "No audio streams found" in str(exc_info.value)
