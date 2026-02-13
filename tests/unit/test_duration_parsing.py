from gopilot.gopro.commands import parse_duration_seconds


def test_parse_duration_seconds_seconds():
    assert parse_duration_seconds("record for 15 seconds") == 15


def test_parse_duration_seconds_minutes():
    assert parse_duration_seconds("capture for 2 min") == 120


def test_parse_duration_seconds_missing_duration():
    assert parse_duration_seconds("start recording now") is None
