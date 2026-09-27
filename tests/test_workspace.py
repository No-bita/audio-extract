import os
import time

from audio_engine.workspace import WorkspaceManager


def test_workspace_directories_creation(tmp_path):
    wm = WorkspaceManager(str(tmp_path))
    assert os.path.exists(wm.sources_dir)
    assert os.path.exists(wm.jobs_dir)
    assert os.path.exists(wm.temp_dir)


def test_workspace_cached_source(tmp_path):
    wm = WorkspaceManager(str(tmp_path))
    video_id = "dQw4w9WgXcQ"
    cached_file = os.path.join(wm.sources_dir, f"{video_id}.webm")

    # Before creating file
    assert wm.get_cached_source(video_id) is None

    # Write dummy source file
    with open(cached_file, "wb") as f:
        f.write(b"test audio data")

    found = wm.get_cached_source(video_id)
    assert found == cached_file


def test_workspace_ttl_cleanup(tmp_path):
    wm = WorkspaceManager(str(tmp_path))

    old_source = os.path.join(wm.sources_dir, "old_vid.opus")
    with open(old_source, "wb") as f:
        f.write(b"old source")

    # Set modification time back 2 hours
    past_time = time.time() - 7200
    os.utime(old_source, (past_time, past_time))

    # Clean with source_ttl of 1 hour (3600s)
    wm.cleanup_expired(source_ttl=3600.0, artifact_ttl=3600.0)

    assert not os.path.exists(old_source)
