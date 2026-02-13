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
