from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv


DEFAULT_SYSTEM_INSTRUCTION = (
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


LLMProvider = Literal["gemini", "openai", "claude"]


@dataclass(frozen=True)
class LLMConfig:
    provider: LLMProvider
    api_key: str
    model_name: str
    system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION


@dataclass(frozen=True)
class ConfigProfile:
    name: str
    mode: str
    shutter_duration_s: int
    settings: dict[str, int]


PROFILES: dict[str, ConfigProfile] = {
    "indoor_photo": ConfigProfile(
        name="indoor_photo",
        mode="photo",
        shutter_duration_s=0,
        settings={"17": 12, "19": 3, "15": -1},
    ),
    "outdoor_video": ConfigProfile(
        name="outdoor_video",
        mode="video",
        shutter_duration_s=30,
        settings={"2": 9, "3": 8, "4": 0},
    ),
    "vlog_walk": ConfigProfile(
        name="vlog_walk",
        mode="video",
        shutter_duration_s=60,
        settings={"2": 9, "3": 5, "4": 4},
    ),
}


@dataclass(frozen=True)
class GoProConfig:
    host: str = "10.5.5.9"
    timeout_seconds: int = 3
    retry_attempts: int = 2
    retry_backoff_seconds: float = 0.25
    circuit_breaker_threshold: int = 3
    circuit_breaker_reset_seconds: float = 8.0


@dataclass(frozen=True)
class AppConfig:
    llm: LLMConfig
    gopro: GoProConfig
    profile: ConfigProfile


def _load_llm_config() -> LLMConfig:
    provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    model_name = os.getenv("LLM_MODEL")

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY. Add it to .env")
        return LLMConfig(
            provider="gemini",
            api_key=api_key,
            model_name=model_name or "gemini-1.5-flash",
        )

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY. Add it to .env")
        return LLMConfig(
            provider="openai",
            api_key=api_key,
            model_name=model_name or "gpt-4o-mini",
        )

    if provider == "claude":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Missing ANTHROPIC_API_KEY. Add it to .env")
        return LLMConfig(
            provider="claude",
            api_key=api_key,
            model_name=model_name or "claude-3-5-sonnet-20241022",
        )

    raise RuntimeError("Unknown LLM_PROVIDER. Supported: gemini, openai, claude")


def load_config() -> AppConfig:
    load_dotenv()

    host = os.getenv("GOPRO_HOST", "10.5.5.9")
    timeout_s = int(os.getenv("GOPRO_TIMEOUT_SECONDS", "3"))
    profile_name = os.getenv("GOPRO_PROFILE", "outdoor_video")

    if profile_name not in PROFILES:
        available = ", ".join(sorted(PROFILES))
        raise RuntimeError(f"Unknown GOPRO_PROFILE '{profile_name}'. Available: {available}")

    gopro = GoProConfig(
        host=host,
        timeout_seconds=timeout_s,
        retry_attempts=int(os.getenv("GOPRO_RETRY_ATTEMPTS", "2")),
        retry_backoff_seconds=float(os.getenv("GOPRO_RETRY_BACKOFF_SECONDS", "0.25")),
        circuit_breaker_threshold=int(os.getenv("GOPRO_CIRCUIT_THRESHOLD", "3")),
        circuit_breaker_reset_seconds=float(os.getenv("GOPRO_CIRCUIT_RESET_SECONDS", "8")),
    )

    return AppConfig(llm=_load_llm_config(), gopro=gopro, profile=PROFILES[profile_name])
