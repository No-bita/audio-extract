from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from audio_engine.models import VideoMetadata
from audio_engine.workspace import WorkspaceManager


@pytest.fixture
def client(tmp_path):
    # Setup test workspace and client
    with patch("app.main.check_system_dependencies"):
        with TestClient(app) as test_client:
            workspace = WorkspaceManager(str(tmp_path))
            app.state.workspace = workspace
            app.state.job_service.workspace = workspace
            yield test_client


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert "status" in res.json()


@patch("app.routes.inspect.Downloader.inspect")
def test_inspect_endpoint_success(mock_inspect, client):
    mock_inspect.return_value = VideoMetadata(
        video_id="dQw4w9WgXcQ",
        source_id="yt_dQw4w9WgXcQ",
        title="Never Gonna Give You Up",
        channel="Rick Astley",
        duration=212.0,
        duration_formatted="03:32",
        thumbnail_url="https://example.com/thumb.jpg",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    )

    res = client.post("/api/inspect", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    assert res.status_code == 200
    data = res.json()
    assert data["source_id"] == "yt_dQw4w9WgXcQ"
    assert data["duration_formatted"] == "03:32"


def test_create_job_validation_full_with_timestamps(client):
    res = client.post(
        "/api/jobs",
        json={
            "source_id": "yt_dQw4w9WgXcQ",
            "operation": "full",
            "start": "00:10",
        },
    )
    assert res.status_code == 422


def test_create_job_validation_clip_missing_timestamps(client):
    res = client.post(
        "/api/jobs",
        json={
            "source_id": "yt_dQw4w9WgXcQ",
            "operation": "clip",
        },
    )
    assert res.status_code == 422


def test_create_job_unknown_source(client):
    res = client.post(
        "/api/jobs",
        json={
            "source_id": "yt_unknown123",
            "operation": "full",
        },
    )
    assert res.status_code == 404


@patch("audio_engine.downloader.Downloader.download_source")
@patch("audio_engine.processor.AudioProcessor.convert_full_audio")
def test_full_job_execution_lifecycle(mock_convert, mock_dl, client, tmp_path):
    # 1. Register metadata via inspect
    with patch("app.routes.inspect.Downloader.inspect") as mock_inspect:
        mock_inspect.return_value = VideoMetadata(
            video_id="dQw4w9WgXcQ",
            source_id="yt_dQw4w9WgXcQ",
            title="Rick Astley",
            channel="Rick Astley",
            duration=212.0,
            duration_formatted="03:32",
            thumbnail_url="https://example.com/thumb.jpg",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        client.post("/api/inspect", json={"url": "https://youtu.be/dQw4w9WgXcQ"})

    dummy_source = tmp_path / "dummy.opus"
    dummy_source.write_bytes(b"dummy audio")
    mock_dl.return_value = str(dummy_source)

    # 2. Trigger job
    res = client.post(
        "/api/jobs",
        json={"source_id": "yt_dQw4w9WgXcQ", "operation": "full"},
    )
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    # 3. Check status
    res_status = client.get(f"/api/jobs/{job_id}")
    assert res_status.status_code == 200
    data = res_status.json()
    assert data["status"] in ("completed", "processing")

    # Manually ensure job output file exists to test stream & download
    job = client.app.state.job_service.jobs[job_id]
    job.status = "completed"
    job.output_path = str(dummy_source)

    # Test /stream
    res_stream = client.get(f"/api/jobs/{job_id}/stream")
    assert res_stream.status_code == 200
    assert res_stream.headers["content-type"] == "audio/mpeg"

    # Test /download
    res_download = client.get(f"/api/jobs/{job_id}/download")
    assert res_download.status_code == 200
    assert "attachment" in res_download.headers.get("content-disposition", "")


@patch("audio_engine.downloader.Downloader.download_source")
@patch("audio_engine.processor.AudioProcessor.trim_audio")
def test_clip_job_execution_lifecycle(mock_trim, mock_dl, client, tmp_path):
    # 1. Register metadata
    with patch("app.routes.inspect.Downloader.inspect") as mock_inspect:
        mock_inspect.return_value = VideoMetadata(
            video_id="dQw4w9WgXcQ",
            source_id="yt_dQw4w9WgXcQ",
            title="Song Title",
            channel="Artist",
            duration=300.0,
            duration_formatted="05:00",
            thumbnail_url="https://example.com/thumb.jpg",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        client.post("/api/inspect", json={"url": "https://youtu.be/dQw4w9WgXcQ"})

    dummy_source = tmp_path / "dummy.opus"
    dummy_source.write_bytes(b"dummy audio")
    mock_dl.return_value = str(dummy_source)

    # 2. Trigger Clip job
    res = client.post(
        "/api/jobs",
        json={
            "source_id": "yt_dQw4w9WgXcQ",
            "operation": "clip",
            "start": "01:00",
            "end": "02:30",
        },
    )
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    # Verify background execution resolved 60.0s to 150.0s
    mock_trim.assert_called_once()
    args, kwargs = mock_trim.call_args
    assert kwargs["start_sec"] == 60.0
    assert kwargs["end_sec"] == 150.0
    assert kwargs["expected_duration"] == 90.0
