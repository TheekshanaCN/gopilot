from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str
    model_name: str = "gemini-3-flash-preview"
    system_instruction: str = (
        "You are a command parser for a GoPro camera.\n\n"
        "Decide:\n"
        "- mode: photo, video, timelapse\n"
        "- action: start, stop, none\n\n"
        "Return JSON ONLY:\n"
        "{\n"
        '  "mode": "photo|video|timelapse",\n'
        '  "action": "start|stop|none"\n'
        "}\n\n"
        "Rules:\n"
        '- "take photo", "capture", "shoot" => photo + start\n'
        '- "record", "take a video", "start video" => video + start\n'
        '- "stop", "stop recording" => action stop\n'
        '- "timelapse" => timelapse (+ start if implied)\n'
        "If unclear, pick the closest."
    )


@dataclass(frozen=True)
class GoProConfig:
    host: str = "10.5.5.9"
    timeout_seconds: int = 3


@dataclass(frozen=True)
class AppConfig:
    gemini: GeminiConfig
    gopro: GoProConfig


def load_config() -> AppConfig:
    load_dotenv()

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise RuntimeError("Missing GEMINI_API_KEY. Add it to .env")

    host = os.getenv("GOPRO_HOST", "10.5.5.9")
    timeout_s = int(os.getenv("GOPRO_TIMEOUT_SECONDS", "3"))

    gopro = GoProConfig(host=host, timeout_seconds=timeout_s)

    return AppConfig(gemini=GeminiConfig(api_key=gemini_api_key), gopro=gopro)
