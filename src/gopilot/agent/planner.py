from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import google.generativeai as genai

from gopilot.config import GeminiConfig
from gopilot.gopro.commands import CameraIntent, intent_from_model_payload, parse_duration_seconds


logger = logging.getLogger(__name__)


class _Mode(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    TIMELAPSE = "timelapse"


class _Action(str, Enum):
    START = "start"
    STOP = "stop"
    NONE = "none"


@dataclass(frozen=True)
class _ParsedModelCommand:
    mode: _Mode
    action: _Action
    confidence: float
    ambiguity: bool
    clarification: str | None

    def as_payload(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "action": self.action.value,
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "clarification": self.clarification,
        }

    @classmethod
    def fallback(cls, reason: str) -> "_ParsedModelCommand":
        return cls(
            mode=_Mode.VIDEO,
            action=_Action.NONE,
            confidence=0.0,
            ambiguity=True,
            clarification=f"I could not parse that command ({reason}). Can you clarify the mode and action?",
        )

    @classmethod
    def validate(cls, payload: dict[str, Any]) -> "_ParsedModelCommand":
        mode = _Mode(str(payload["mode"]).lower())
        action = _Action(str(payload["action"]).lower())

        confidence = float(payload.get("confidence", 1.0))
        confidence = max(0.0, min(1.0, confidence))
        ambiguity = bool(payload.get("ambiguity", False))
        clarification_raw = payload.get("clarification")
        clarification = str(clarification_raw).strip() if clarification_raw else None

        if ambiguity or confidence < 0.6:
            action = _Action.NONE
            if not clarification:
                clarification = "I am not fully confident. Should I start, stop, or do nothing?"

        return cls(
            mode=mode,
            action=action,
            confidence=confidence,
            ambiguity=ambiguity,
            clarification=clarification,
        )


class ShotPlanner:
    def __init__(
        self,
        config: GeminiConfig,
        api_retries: int = 2,
        initial_backoff_s: float = 0.5,
    ):
        genai.configure(api_key=config.api_key)
        self._model = genai.GenerativeModel(
            model_name=config.model_name,
            system_instruction=config.system_instruction,
        )
        self._api_retries = api_retries
        self._initial_backoff_s = initial_backoff_s

    @staticmethod
    def _sanitize_response_text(response_text: str) -> str:
        sanitized = " ".join(response_text.strip().split())
        return sanitized[:1000]

    def _generate_with_retry(self, user_prompt: str) -> str:
        attempts = self._api_retries + 1
        delay_s = self._initial_backoff_s

        for attempt in range(1, attempts + 1):
            try:
                response = self._model.generate_content(user_prompt)
                return response.text
            except Exception:
                if attempt == attempts:
                    raise
                time.sleep(delay_s)
                delay_s *= 2

        raise RuntimeError("unreachable")

    def _ask_model(self, user_prompt: str) -> dict[str, Any]:
        logger.debug("AI prompt=%s", user_prompt)
        try:
            raw_response = self._generate_with_retry(user_prompt)
        except Exception as exc:
            fallback = _ParsedModelCommand.fallback(f"model_api_failure:{type(exc).__name__}")
            logger.warning("Model API failed. fallback=%s", fallback.as_payload())
            return fallback.as_payload()

        sanitized_response = self._sanitize_response_text(raw_response)
        logger.debug("AI sanitized_response=%s", sanitized_response)

        try:
            payload = json.loads(raw_response.strip())
        except json.JSONDecodeError:
            fallback = _ParsedModelCommand.fallback("invalid_json")
            logger.warning("Invalid JSON from model. response=%s fallback=%s", sanitized_response, fallback.as_payload())
            return fallback.as_payload()

        if not isinstance(payload, dict):
            fallback = _ParsedModelCommand.fallback("schema_mismatch")
            logger.warning("Schema mismatch from model. payload=%s fallback=%s", payload, fallback.as_payload())
            return fallback.as_payload()

        try:
            parsed = _ParsedModelCommand.validate(payload)
        except (KeyError, TypeError, ValueError):
            fallback = _ParsedModelCommand.fallback("schema_mismatch")
            logger.warning("Schema validation failure. payload=%s fallback=%s", payload, fallback.as_payload())
            return fallback.as_payload()

        logger.debug("AI parsed_command=%s", parsed.as_payload())
        return parsed.as_payload()

    def plan(self, user_prompt: str) -> CameraIntent:
        duration_s = parse_duration_seconds(user_prompt)
        ai_payload = self._ask_model(user_prompt)
        intent = intent_from_model_payload(ai_payload, duration_s=duration_s)
        logger.info("Final command=%s", intent)
        return intent
