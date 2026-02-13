from __future__ import annotations

import json

import google.generativeai as genai

from gopilot.config import GeminiConfig
from gopilot.gopro.commands import CameraIntent, intent_from_model_payload, parse_duration_seconds


class ShotPlanner:
    def __init__(self, config: GeminiConfig):
        genai.configure(api_key=config.api_key)
        self._model = genai.GenerativeModel(
            model_name=config.model_name,
            system_instruction=config.system_instruction,
        )

    def _ask_model(self, user_prompt: str) -> dict:
        response = self._model.generate_content(user_prompt)
        return json.loads(response.text.strip())

    def plan(self, user_prompt: str) -> CameraIntent:
        duration_s = parse_duration_seconds(user_prompt)
        ai_payload = self._ask_model(user_prompt)
        return intent_from_model_payload(ai_payload, duration_s=duration_s)
