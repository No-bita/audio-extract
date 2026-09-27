"""Domain exceptions for the audio engine with user-friendly error translations."""


class AudioEngineError(Exception):
    """Base class for all audio engine exceptions."""
    user_message: str = "An unexpected error occurred while processing the audio."

    def __init__(self, message: str = "", user_message: str = ""):
        super().__init__(message or self.user_message)
        if user_message:
            self.user_message = user_message


class InvalidURLError(AudioEngineError):
    user_message = "Please provide a valid YouTube video URL (e.g., https://www.youtube.com/watch?v=... or https://youtu.be/...)."


class PlaylistNotAllowedError(AudioEngineError):
    user_message = "Playlists are not supported. Please provide a direct link to a single video."


class VideoUnavailableError(AudioEngineError):
    user_message = "This video couldn't be accessed. It may be private, restricted, unavailable, or geo-blocked."


class MetadataExtractionError(AudioEngineError):
    user_message = "Could not retrieve video information. Check your internet connection or the URL."


class SourceNotFoundError(AudioEngineError):
    user_message = "This video session has expired or was not found. Please inspect the YouTube URL again."


class DownloadError(AudioEngineError):
    user_message = "Failed to download the audio stream from YouTube."


class DependencyNotFoundError(AudioEngineError):
    user_message = "A required system dependency (ffmpeg or ffprobe) was not found."


class InvalidTimestampError(AudioEngineError):
    user_message = "The timestamp format is invalid. Use SS, MM:SS, HH:MM:SS, or -MM:SS."


class InvalidClipRangeError(AudioEngineError):
    user_message = "Invalid clip range. Ensure the start time is before the end time and within video duration."


class ProcessingError(AudioEngineError):
    user_message = "An error occurred while encoding or clipping the MP3 with FFmpeg."
