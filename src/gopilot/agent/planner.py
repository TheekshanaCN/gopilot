from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from gopilot.config import LLMConfig
from gopilot.gopro.commands import CameraIntent, intent_from_model_payload, parse_duration_seconds


logger = logging.getLogger(__name__)


class CommandMode(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    TIMELAPSE = "timelapse"


class CommandAction(str, Enum):
    START = "start"
    STOP = "stop"
    NONE = "none"


@dataclass(frozen=True)
class ParsedModelCommand:
    mode: CommandMode
    action: CommandAction
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
    def fallback(cls, reason: str) -> "ParsedModelCommand":
        return cls(
            mode=CommandMode.VIDEO,
            action=CommandAction.NONE,
            confidence=0.0,
            ambiguity=True,
            clarification=f"I could not parse that command ({reason}). Can you clarify the mode and action?",
        )

    @classmethod
    def validate(cls, payload: dict[str, Any]) -> "ParsedModelCommand":
        mode = CommandMode(str(payload["mode"]).lower())
        action = CommandAction(str(payload["action"]).lower())

        confidence = float(payload.get("confidence", 1.0))
        confidence = max(0.0, min(1.0, confidence))
        ambiguity = bool(payload.get("ambiguity", False))
        clarification_raw = payload.get("clarification")
        clarification = str(clarification_raw).strip() if clarification_raw else None

        if ambiguity or confidence < 0.6:
            action = CommandAction.NONE
            if not clarification:
                clarification = "I am not fully confident. Should I start, stop, or do nothing?"

        return cls(
            mode=mode,
            action=action,
            confidence=confidence,
            ambiguity=ambiguity,
            clarification=clarification,
        )


class LLMClient(Protocol):
    def generate(self, user_prompt: str) -> str:
        ...


class GeminiClient:
    def __init__(self, config: LLMConfig):
        import google.generativeai as genai

        genai.configure(api_key=config.api_key)
        self._model = genai.GenerativeModel(
            model_name=config.model_name,
            system_instruction=config.system_instruction,
        )

    def generate(self, user_prompt: str) -> str:
        response = self._model.generate_content(user_prompt)
        return response.text


class OpenAIClient:
    def __init__(self, config: LLMConfig):
        from openai import OpenAI

        self._client = OpenAI(api_key=config.api_key)
        self._model_name = config.model_name
        self._system_instruction = config.system_instruction

    def generate(self, user_prompt: str) -> str:
        completion = self._client.chat.completions.create(
            model=self._model_name,
            messages=[
                {"role": "system", "content": self._system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        return completion.choices[0].message.content or "{}"


class ClaudeClient:
    def __init__(self, config: LLMConfig):
        from anthropic import Anthropic

        self._client = Anthropic(api_key=config.api_key)
        self._model_name = config.model_name
        self._system_instruction = config.system_instruction

    def generate(self, user_prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model_name,
            max_tokens=256,
            temperature=0,
            system=self._system_instruction,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_blocks = [block.text for block in response.content if getattr(block, "type", "") == "text"]
        return "\n".join(text_blocks) if text_blocks else "{}"


def validate_model_command_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return ParsedModelCommand.validate(payload).as_payload()


def create_llm_client(config: LLMConfig) -> LLMClient:
    if config.provider == "gemini":
        return GeminiClient(config)
    if config.provider == "openai":
        return OpenAIClient(config)
    if config.provider == "claude":
        return ClaudeClient(config)
    raise ValueError(f"Unsupported provider: {config.provider}")


class ShotPlanner:
    def __init__(
        self,
        config: LLMConfig,
        api_retries: int = 2,
        initial_backoff_s: float = 0.5,
    ):
        self._client = create_llm_client(config)
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
                return self._client.generate(user_prompt)
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
            fallback = ParsedModelCommand.fallback(f"model_api_failure:{type(exc).__name__}")
            logger.warning("Model API failed. fallback=%s", fallback.as_payload())
            return fallback.as_payload()

        sanitized_response = self._sanitize_response_text(raw_response)
        logger.debug("AI sanitized_response=%s", sanitized_response)

        try:
            payload = json.loads(raw_response.strip())
        except json.JSONDecodeError:
            fallback = ParsedModelCommand.fallback("invalid_json")
            logger.warning("Invalid JSON from model. response=%s fallback=%s", sanitized_response, fallback.as_payload())
            return fallback.as_payload()

        if not isinstance(payload, dict):
            fallback = ParsedModelCommand.fallback("schema_mismatch")
            logger.warning("Schema mismatch from model. payload=%s fallback=%s", payload, fallback.as_payload())
            return fallback.as_payload()

        try:
            parsed = ParsedModelCommand.validate(payload)
        except (KeyError, TypeError, ValueError):
            fallback = ParsedModelCommand.fallback("schema_mismatch")
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
