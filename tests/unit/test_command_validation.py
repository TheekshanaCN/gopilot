import pytest

from gopilot.agent.planner import validate_model_command_payload


def test_validate_model_payload_keeps_high_confidence_action():
    payload = validate_model_command_payload({"mode": "video", "action": "start", "confidence": 0.95})
    assert payload["action"] == "start"
    assert payload["mode"] == "video"


def test_validate_model_payload_downgrades_ambiguous_to_none():
    payload = validate_model_command_payload({"mode": "video", "action": "start", "ambiguity": True})
    assert payload["action"] == "none"
    assert payload["clarification"]


def test_validate_model_payload_rejects_invalid_action():
    with pytest.raises(ValueError):
        validate_model_command_payload({"mode": "video", "action": "launch"})
