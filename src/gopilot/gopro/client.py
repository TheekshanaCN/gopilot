from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

import requests

from gopilot.config import GoProConfig
from gopilot.gopro.commands import (
    CameraMode,
    Hero7Endpoint,
    Hero7Setting,
    Hero7Shutter,
    camera_mode_from_hero7_value,
    capture_state_from_shutter_value,
    hero7_setting_path,
    hero7_mode_from_camera_mode,
)
from gopilot.logging import get_logger

logger = get_logger(__name__)


class GoProClientError(RuntimeError):
    pass


class GoProTimeoutError(GoProClientError):
    pass


class GoProResponseError(GoProClientError):
    def __init__(self, status_code: int, url: str, body: str | None = None):
        message = f"GoPro request failed ({status_code}) for {url}"
        if body:
            message = f"{message}: {body.strip()[:200]}"
        super().__init__(message)
        self.status_code = status_code
        self.url = url
        self.body = body


class CircuitBreakerOpenError(GoProClientError):
    pass


class GoProClient:
    def __init__(self, config: Optional[GoProConfig] = None):
        self._config = config or GoProConfig()
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    def _build_url(self, endpoint: Hero7Endpoint | str) -> str:
        path = endpoint.value if isinstance(endpoint, Hero7Endpoint) else endpoint
        return f"http://{self._config.host}{path}"

    def _check_circuit(self) -> None:
        if self._opened_at is None:
            return
        elapsed = time.monotonic() - self._opened_at
        if elapsed >= self._config.circuit_breaker_reset_seconds:
            self._opened_at = None
            self._consecutive_failures = 0
            logger.info("Circuit breaker reset")
            return
        raise CircuitBreakerOpenError("GoPro circuit breaker is open; refusing request")

    def _record_success(self) -> None:
        self._consecutive_failures = 0
        self._opened_at = None

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._config.circuit_breaker_threshold:
            self._opened_at = time.monotonic()
            logger.warning("Circuit breaker opened after repeated GoPro failures")

    def _request(self, path: Hero7Endpoint | str, params: Optional[dict[str, Any]] = None) -> requests.Response:
        self._check_circuit()
        url = self._build_url(path)
        delay_s = self._config.retry_backoff_seconds
        attempts = self._config.retry_attempts + 1

        for attempt in range(1, attempts + 1):
            try:
                response = requests.get(url, params=params, timeout=self._config.timeout_seconds)
                if response.status_code == 200:
                    self._record_success()
                    return response

                if 500 <= response.status_code < 600 and attempt < attempts:
                    self._record_failure()
                    logger.warning("Retrying GoPro request after server error", extra={"status_code": response.status_code})
                    time.sleep(delay_s)
                    delay_s *= 2
                    continue

                self._record_failure()
                raise GoProResponseError(response.status_code, response.url, response.text)
            except requests.Timeout as exc:
                self._record_failure()
                if attempt == attempts:
                    raise GoProTimeoutError(f"GoPro request timed out for {url}") from exc
                time.sleep(delay_s)
                delay_s *= 2
            except requests.RequestException as exc:
                self._record_failure()
                if attempt == attempts:
                    raise GoProClientError(f"GoPro request error for {url}: {exc}") from exc
                time.sleep(delay_s)
                delay_s *= 2

        raise GoProClientError(f"GoPro request failed after retries for {url}")

    @staticmethod
    def _safe_json(response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            return {}
        if isinstance(payload, dict):
            return payload
        return {}

    def set_mode(self, mode: CameraMode | str) -> dict[str, str]:
        hero_mode = hero7_mode_from_camera_mode(mode)
        self._request(Hero7Endpoint.COMMAND_MODE, params={"p": hero_mode.value})
        resolved_mode = CameraMode(mode).value
        return {"mode": resolved_mode}

    def start_shutter(self) -> dict[str, str]:
        self._request(Hero7Endpoint.COMMAND_SHUTTER, params={"p": Hero7Shutter.START.value})
        return {"capture_state": "capturing"}

    def stop_shutter(self) -> dict[str, str]:
        self._request(Hero7Endpoint.COMMAND_SHUTTER, params={"p": Hero7Shutter.STOP.value})
        return {"capture_state": "idle"}

    def start_capture(self) -> dict[str, str]:
        return self.start_shutter()

    def stop_capture(self) -> dict[str, str]:
        return self.stop_shutter()

    def get_status(self) -> dict[str, Any]:
        status_payload = self._safe_json(self._request(Hero7Endpoint.STATUS))
        state_payload = self._safe_json(self._request(Hero7Endpoint.STATE))

        status = status_payload.get("status", {})
        settings = status_payload.get("settings", {})

        mode = camera_mode_from_hero7_value(int(status.get("43", 0))).value
        capture_state = capture_state_from_shutter_value(int(status.get("8", 0)))

        return {
            "mode": mode,
            "capture_state": capture_state,
            "settings": settings,
            "media_count": int(state_payload.get("info", {}).get("media_count", 0)),
        }

    def get_state(self) -> dict[str, Any]:
        return self._safe_json(self._request(Hero7Endpoint.STATE))

    def get_settings(self) -> dict[str, Any]:
        status_payload = self._safe_json(self._request(Hero7Endpoint.STATUS))
        return status_payload.get("settings", {})

    def set_setting(self, key: str | int, value: Any) -> dict[str, Any]:
        setting_id = int(key)
        option_id = int(value)
        self._request(hero7_setting_path(setting_id, option_id))
        return {"key": str(setting_id), "value": option_id}

    def set_setting_enum(self, setting: Hero7Setting, option: int) -> dict[str, Any]:
        return self.set_setting(setting.value, option)

    def list_media(self, limit: int = 50, cursor: Optional[str] = None) -> dict[str, Any]:
        payload = self._safe_json(self._request(Hero7Endpoint.MEDIA_LIST))
        filesystems = payload.get("media", [])
        items: list[dict[str, Any]] = []

        for fs in filesystems:
            folder = fs.get("d", "")
            for entry in fs.get("fs", []):
                filename = entry.get("n")
                if not filename:
                    continue
                media_id = f"{folder}/{filename}" if folder else filename
                size_bytes = int(entry.get("s", 0) or 0)
                created = entry.get("cre") or ""
                items.append(
                    {
                        "id": media_id,
                        "filename": filename,
                        "created_at": str(created),
                        "size_bytes": size_bytes,
                    }
                )

        start = int(cursor) if cursor else 0
        end = start + limit
        paged = items[start:end]
        next_cursor = str(end) if end < len(items) else None
        return {"items": paged, "next_cursor": next_cursor}

    def download_media(self, media_id: str, destination: str) -> dict[str, Any]:
        url = f"http://{self._config.host}/videos/DCIM/{media_id}"
        try:
            response = requests.get(url, timeout=self._config.timeout_seconds, stream=True)
        except requests.Timeout as exc:
            raise GoProTimeoutError(f"GoPro media download timed out for {url}") from exc
        except requests.RequestException as exc:
            raise GoProClientError(f"GoPro media download error for {url}: {exc}") from exc

        if response.status_code != 200:
            raise GoProResponseError(response.status_code, url, response.text)

        target_path = Path(destination)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        bytes_written = 0
        with target_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                handle.write(chunk)
                bytes_written += len(chunk)

        return {
            "media_id": media_id,
            "destination": str(target_path),
            "bytes_written": bytes_written,
        }
