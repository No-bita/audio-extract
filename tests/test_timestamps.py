import pytest

from audio_engine.errors import InvalidClipRangeError, InvalidTimestampError
from audio_engine.timestamps import ClipValidator, TimestampParser, TimestampResolver


# --- TimestampParser Tests ---

def test_parse_seconds_only():
    spec = TimestampParser.parse("45")
    assert spec.raw == "45"
    assert spec.value_seconds == 45.0
    assert not spec.is_relative_end


def test_parse_fractional_seconds():
    spec = TimestampParser.parse("65.250")
    assert spec.value_seconds == 65.25
    assert not spec.is_relative_end


def test_parse_minutes_seconds():
    spec = TimestampParser.parse("01:15")
    assert spec.value_seconds == 75.0
    assert not spec.is_relative_end


def test_parse_hours_minutes_seconds():
    spec = TimestampParser.parse("01:02:03")
    assert spec.value_seconds == 3600 + 120 + 3
    assert not spec.is_relative_end


def test_parse_relative_countdown():
    spec = TimestampParser.parse("-00:30")
    assert spec.raw == "-00:30"
    assert spec.value_seconds == 30.0
    assert spec.is_relative_end


def test_parse_invalid_seconds_over_60():
    with pytest.raises(InvalidTimestampError):
        TimestampParser.parse("01:75")


def test_parse_invalid_characters():
    with pytest.raises(InvalidTimestampError):
        TimestampParser.parse("abc:12")


def test_parse_empty_string():
    with pytest.raises(InvalidTimestampError):
        TimestampParser.parse("   ")


# --- TimestampResolver Tests ---

def test_resolve_standard_forward():
    spec = TimestampParser.parse("01:30")
    resolved = TimestampResolver.resolve(spec, duration=300.0)
    assert resolved == 90.0


def test_resolve_relative_countdown():
    spec = TimestampParser.parse("-01:30")
    resolved = TimestampResolver.resolve(spec, duration=300.0)
    assert resolved == 210.0


def test_resolve_out_of_bounds_forward():
    spec = TimestampParser.parse("05:30")  # 330s
    with pytest.raises(InvalidTimestampError):
        TimestampResolver.resolve(spec, duration=300.0)


def test_resolve_out_of_bounds_negative():
    spec = TimestampParser.parse("-06:00")  # 360s offset on 300s duration -> -60s
    with pytest.raises(InvalidTimestampError):
        TimestampResolver.resolve(spec, duration=300.0)


# --- ClipValidator Tests ---

def test_clip_validator_valid():
    duration = ClipValidator.validate(start_sec=10.0, end_sec=50.0, duration=100.0)
    assert duration == 40.0


def test_clip_validator_start_equal_end():
    with pytest.raises(InvalidClipRangeError):
        ClipValidator.validate(start_sec=50.0, end_sec=50.0, duration=100.0)


def test_clip_validator_start_after_end():
    with pytest.raises(InvalidClipRangeError):
        ClipValidator.validate(start_sec=60.0, end_sec=50.0, duration=100.0)


def test_clip_validator_end_exceeds_duration():
    with pytest.raises(InvalidClipRangeError):
        ClipValidator.validate(start_sec=10.0, end_sec=105.0, duration=100.0)


def test_clip_validator_negative_start():
    with pytest.raises(InvalidClipRangeError):
        ClipValidator.validate(start_sec=-5.0, end_sec=50.0, duration=100.0)
