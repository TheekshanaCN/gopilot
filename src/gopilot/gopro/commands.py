from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class CameraMode(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    TIMELAPSE = "timelapse"


class CameraAction(str, Enum):
    START = "start"
    STOP = "stop"
    NONE = "none"


@dataclass(frozen=True)
class CameraIntent:
    mode: CameraMode = CameraMode.VIDEO
    action: CameraAction = CameraAction.NONE
    duration_s: int | None = None


class Hero7Mode(int, Enum):
    VIDEO = 0
    PHOTO = 1
    TIMELAPSE = 2


class Hero7Shutter(int, Enum):
    STOP = 0
    START = 1


class Hero7Endpoint(str, Enum):
    COMMAND_MODE = "/gp/gpControl/command/mode"
    COMMAND_SHUTTER = "/gp/gpControl/command/shutter"
    COMMAND_SETTING = "/gp/gpControl/setting"
    STATUS = "/gp/gpControl/status"
    STATE = "/gp/gpControl/info"
    MEDIA_LIST = "/gp/gpMediaList"


def hero7_setting_path(setting_id: int, option_id: int) -> str:
    return f"{Hero7Endpoint.COMMAND_SETTING.value}/{setting_id}/{option_id}"


class Hero7Setting(int, Enum):
    VIDEO_RESOLUTION = 2
    VIDEO_FPS = 3
    VIDEO_FOV = 4
    PHOTO_RESOLUTION = 17
    PHOTO_FOV = 19
    TIMELAPSE_INTERVAL = 5
    PROTUNE = 10
    WHITE_BALANCE = 11
    COLOR = 12
    ISO_LIMIT = 13
    SHARPNESS = 14
    EV_COMP = 15


class Hero7Option(int, Enum):
    # Common video values
    RES_1080P = 9
    RES_2K = 4
    RES_4K = 1
    FPS_24 = 6
    FPS_30 = 8
    FPS_60 = 5
    FOV_WIDE = 0
    FOV_SUPERVIEW = 3
    FOV_LINEAR = 4

    # Photo values
    PHOTO_WIDE = 0
    PHOTO_LINEAR = 3

    # ProTune values
    OFF = 0
    ON = 1


_MODE_TO_HERO7: dict[CameraMode, Hero7Mode] = {
    CameraMode.VIDEO: Hero7Mode.VIDEO,
    CameraMode.PHOTO: Hero7Mode.PHOTO,
    CameraMode.TIMELAPSE: Hero7Mode.TIMELAPSE,
}


_CAPTURE_STATE_BY_SHUTTER: dict[int, str] = {
    Hero7Shutter.STOP.value: "idle",
    Hero7Shutter.START.value: "capturing",
}


def hero7_mode_from_camera_mode(mode: CameraMode | str) -> Hero7Mode:
    normalized = CameraMode(mode)
    return _MODE_TO_HERO7[normalized]


def camera_mode_from_hero7_value(value: int) -> CameraMode:
    for mode, hero7_mode in _MODE_TO_HERO7.items():
        if hero7_mode.value == value:
            return mode
    return CameraMode.VIDEO


def capture_state_from_shutter_value(value: int) -> str:
    return _CAPTURE_STATE_BY_SHUTTER.get(value, "idle")


def parse_duration_seconds(text: str) -> int | None:
    t = text.lower().strip()

    seconds = re.search(r"\b(\d+)\s*(s|sec|secs|second|seconds)\b", t)
    if seconds:
        return int(seconds.group(1))

    minutes = re.search(r"\b(\d+)\s*(m|min|mins|minute|minutes)\b", t)
    if minutes:
        return int(minutes.group(1)) * 60

    return None


def intent_from_model_payload(payload: dict[str, Any], duration_s: int | None = None) -> CameraIntent:
    mode_value = str(payload.get("mode", CameraMode.VIDEO.value)).lower()
    action_value = str(payload.get("action", CameraAction.NONE.value)).lower()

    mode = CameraMode(mode_value) if mode_value in CameraMode._value2member_map_ else CameraMode.VIDEO
    action = (
        CameraAction(action_value)
        if action_value in CameraAction._value2member_map_
        else CameraAction.NONE
    )

    return CameraIntent(mode=mode, action=action, duration_s=duration_s)
