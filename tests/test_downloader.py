import pytest
from unittest.mock import MagicMock, patch

from audio_engine.downloader import Downloader, format_duration, normalize_youtube_url
from audio_engine.errors import (
    InvalidURLError,
    MetadataExtractionError,
    PlaylistNotAllowedError,
    VideoUnavailableError,
)


def test_format_duration():
    assert format_duration(0) == "00:00"
    assert format_duration(45) == "00:45"
    assert format_duration(75) == "01:15"
    assert format_duration(3665) == "01:01:05"


def test_normalize_youtube_url_valid_watch():
    video_id, url = normalize_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert video_id == "dQw4w9WgXcQ"
    assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_normalize_youtube_url_strip_playlist():
    video_id, url = normalize_youtube_url(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDdQw4w9WgXcQ&start_radio=1"
    )
    assert video_id == "dQw4w9WgXcQ"
    assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_normalize_youtube_url_shortlink():
    video_id, url = normalize_youtube_url("https://youtu.be/dQw4w9WgXcQ")
    assert video_id == "dQw4w9WgXcQ"
    assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_normalize_youtube_url_shorts():
    video_id, url = normalize_youtube_url("https://youtube.com/shorts/dQw4w9WgXcQ?feature=share")
    assert video_id == "dQw4w9WgXcQ"
    assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_normalize_youtube_url_pure_playlist_rejected():
    with pytest.raises(PlaylistNotAllowedError):
        normalize_youtube_url("https://www.youtube.com/playlist?list=PL1234567890ABCDEF")


def test_normalize_youtube_url_invalid_domain():
    with pytest.raises(InvalidURLError):
        normalize_youtube_url("https://vimeo.com/12345678")


def test_normalize_youtube_url_invalid_id():
    with pytest.raises(InvalidURLError):
        normalize_youtube_url("https://www.youtube.com/watch?v=short")


@patch("audio_engine.downloader.yt_dlp.YoutubeDL")
def test_inspect_success(mock_ydl_class):
    mock_instance = MagicMock()
    mock_instance.extract_info.return_value = {
        "id": "dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up",
        "uploader": "Rick Astley",
        "duration": 212.0,
        "thumbnail": "https://example.com/thumb.jpg",
    }
    mock_ydl_class.return_value.__enter__.return_value = mock_instance

    metadata = Downloader.inspect("https://youtu.be/dQw4w9WgXcQ")
    assert metadata.video_id == "dQw4w9WgXcQ"
    assert metadata.source_id == "yt_dQw4w9WgXcQ"
    assert metadata.title == "Never Gonna Give You Up"
    assert metadata.channel == "Rick Astley"
    assert metadata.duration == 212.0
    assert metadata.duration_formatted == "03:32"
    assert metadata.thumbnail_url == "https://example.com/thumb.jpg"


@patch("audio_engine.downloader.yt_dlp.YoutubeDL")
def test_inspect_video_unavailable(mock_ydl_class):
    import yt_dlp

    mock_instance = MagicMock()
    mock_instance.extract_info.side_effect = yt_dlp.utils.DownloadError("Video unavailable: private video")
    mock_ydl_class.return_value.__enter__.return_value = mock_instance

    with pytest.raises(VideoUnavailableError):
        Downloader.inspect("https://youtu.be/dQw4w9WgXcQ")
