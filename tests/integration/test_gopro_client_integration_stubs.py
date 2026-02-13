from unittest.mock import MagicMock, patch

from gopilot.config import GoProConfig
from gopilot.gopro.client import GoProClient


def _response(status_code: int, payload: dict):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.url = "http://10.5.5.9/mock"
    response.text = ""
    return response


@patch("gopilot.gopro.client.requests.get")
def test_get_status_with_mocked_responses(mock_get):
    mock_get.side_effect = [
        _response(200, {"status": {"43": 0, "8": 1}, "settings": {"2": 9}}),
        _response(200, {"info": {"media_count": 7}}),
    ]

    client = GoProClient(GoProConfig())
    result = client.get_status()

    assert result["mode"] == "video"
    assert result["capture_state"] == "capturing"
    assert result["media_count"] == 7


@patch("gopilot.gopro.client.requests.get")
def test_list_media_with_mocked_response(mock_get):
    mock_get.return_value = _response(
        200,
        {"media": [{"d": "100GOPRO", "fs": [{"n": "GX010001.MP4", "s": 2048, "cre": "12345"}]}]},
    )

    client = GoProClient(GoProConfig())
    result = client.list_media(limit=5)

    assert result["items"][0]["id"] == "100GOPRO/GX010001.MP4"
