from __future__ import annotations

import requests

from gopilot.config import GoProConfig
from gopilot.gopro.commands import CameraMode


class GoProClient:
    def __init__(self, config: GoProConfig):
        self._config = config

    def send(self, url: str) -> None:
        response = requests.get(url, timeout=self._config.timeout_seconds)
        if response.status_code != 200:
            raise RuntimeError(f"GoPro command failed: {response.status_code} for {url}")

    def set_mode(self, mode: CameraMode) -> None:
        self.send(self._config.mode_urls[mode.value])

    def start_shutter(self) -> None:
        self.send(self._config.shutter_urls["start"])

    def stop_shutter(self) -> None:
        self.send(self._config.shutter_urls["stop"])
