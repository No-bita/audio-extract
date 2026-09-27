from audio_engine.errors import InvalidClipRangeError, InvalidTimestampError
from audio_engine.models import TimestampSpec


class TimestampParser:
    """Parses raw timestamp strings into syntax-only TimestampSpec."""

    @staticmethod
    def parse(time_str: str) -> TimestampSpec:
        if not time_str or not isinstance(time_str, str):
            raise InvalidTimestampError("Timestamp cannot be empty.")

        raw = time_str.strip()
        is_negative = raw.startswith("-")
        work_str = raw[1:].strip() if is_negative else raw

        if not work_str:
            raise InvalidTimestampError("Timestamp value cannot be empty.")

        parts = work_str.split(":")
        try:
            numeric_parts = [float(p) for p in parts]
        except ValueError:
            raise InvalidTimestampError(f"Invalid characters in timestamp: '{raw}'")

        for val in numeric_parts:
            if val < 0:
                raise InvalidTimestampError(f"Negative components inside timestamp are invalid: '{raw}'")

        if len(numeric_parts) == 1:
            # Format: 'SS' or 'SS.ms'
            value_seconds = numeric_parts[0]
        elif len(numeric_parts) == 2:
            # Format: 'MM:SS'
            mins, secs = numeric_parts
            if secs >= 60.0:
                raise InvalidTimestampError(f"Seconds component must be less than 60 in '{raw}'.")
            value_seconds = mins * 60.0 + secs
        elif len(numeric_parts) == 3:
            # Format: 'HH:MM:SS'
            hours, mins, secs = numeric_parts
            if mins >= 60.0:
                raise InvalidTimestampError(f"Minutes component must be less than 60 in '{raw}'.")
            if secs >= 60.0:
                raise InvalidTimestampError(f"Seconds component must be less than 60 in '{raw}'.")
            value_seconds = hours * 3600.0 + mins * 60.0 + secs
        else:
            raise InvalidTimestampError(f"Too many colon-separated fields in timestamp: '{raw}'")

        return TimestampSpec(
            raw=raw,
            value_seconds=value_seconds,
            is_relative_end=is_negative,
        )


class TimestampResolver:
    """Resolves single TimestampSpec against total duration and checks single-boundary bounds."""

    @staticmethod
    def resolve(spec: TimestampSpec, duration: float) -> float:
        if duration <= 0:
            raise InvalidTimestampError("Video duration must be positive to resolve timestamps.")

        if spec.is_relative_end:
            resolved = duration - spec.value_seconds
        else:
            resolved = spec.value_seconds

        if resolved < 0.0 or resolved > duration:
            raise InvalidTimestampError(
                f"Timestamp '{spec.raw}' resolves to {resolved:.2f}s, which is outside the video range (0.00s - {duration:.2f}s)."
            )

        return resolved


class ClipValidator:
    """Validates the pair of start and end times and derives clip interval."""

    @staticmethod
    def validate(start_sec: float, end_sec: float, duration: float) -> float:
        if start_sec < 0.0:
            raise InvalidClipRangeError(f"Start time ({start_sec:.2f}s) cannot be negative.")
        if end_sec > duration:
            raise InvalidClipRangeError(
                f"End time ({end_sec:.2f}s) exceeds total video duration ({duration:.2f}s)."
            )
        if start_sec >= end_sec:
            raise InvalidClipRangeError(
                f"Start time ({start_sec:.2f}s) must be strictly before end time ({end_sec:.2f}s)."
            )

        clip_duration = end_sec - start_sec
        if clip_duration < 0.1:
            raise InvalidClipRangeError("Clip duration must be at least 0.1 seconds.")

        return clip_duration
