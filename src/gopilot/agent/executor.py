from __future__ import annotations

import time

from gopilot.gopro.client import GoProClient
from gopilot.gopro.commands import CameraAction, CameraIntent, CameraMode


class CommandExecutor:
    def __init__(self, client: GoProClient, retries: int = 2, retry_delay_s: float = 0.5):
        self._client = client
        self._retries = retries
        self._retry_delay_s = retry_delay_s

    def _run_with_retry(self, action_name: str, operation) -> None:
        attempts = self._retries + 1
        for attempt in range(1, attempts + 1):
            try:
                operation()
                return
            except Exception:
                if attempt == attempts:
                    raise RuntimeError(f"Failed to execute {action_name} after {attempts} attempts")
                time.sleep(self._retry_delay_s)

    def execute(self, intent: CameraIntent) -> None:
        self._run_with_retry(f"set_mode:{intent.mode.value}", lambda: self._client.set_mode(intent.mode))
        print(f"🎥 Mode set to {intent.mode.value.upper()}")

        if intent.action == CameraAction.START:
            self._run_with_retry("shutter_start", self._client.start_shutter)
            print("🔴 Shutter START")

            if intent.duration_s and intent.duration_s > 0 and intent.mode in (CameraMode.VIDEO, CameraMode.TIMELAPSE):
                print(f"⏱️ Waiting {intent.duration_s}s then STOP...")
                time.sleep(intent.duration_s)
                self._run_with_retry("shutter_stop", self._client.stop_shutter)
                print("⏹️ Shutter STOP")

        elif intent.action == CameraAction.STOP:
            self._run_with_retry("shutter_stop", self._client.stop_shutter)
            print("⏹️ Shutter STOP")
