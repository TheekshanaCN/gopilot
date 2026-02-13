from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


CameraMode = Literal["photo", "video", "timelapse"]
CaptureState = Literal["idle", "capturing"]


@dataclass
class GoProClient:
    """Simple GoPro client abstraction used by the MCP server.

    This implementation is intentionally lightweight and in-memory so the MCP
    server can run locally without requiring camera connectivity.
    """

    mode: CameraMode = "video"
    capture_state: CaptureState = "idle"
    settings: Dict[str, Any] = field(default_factory=dict)
    media: List[Dict[str, Any]] = field(default_factory=list)

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "capture_state": self.capture_state,
            "settings": self.settings,
            "media_count": len(self.media),
        }

    def set_mode(self, mode: CameraMode) -> Dict[str, Any]:
        self.mode = mode
        return {"mode": self.mode}

    def start_capture(self) -> Dict[str, Any]:
        self.capture_state = "capturing"
        return {"capture_state": self.capture_state}

    def stop_capture(self) -> Dict[str, Any]:
        self.capture_state = "idle"
        return {"capture_state": self.capture_state}

    def set_setting(self, key: str, value: Any) -> Dict[str, Any]:
        self.settings[key] = value
        return {"key": key, "value": value}

    def list_media(self, limit: int = 50, cursor: Optional[str] = None) -> Dict[str, Any]:
        start = int(cursor) if cursor else 0
        end = start + limit
        items = self.media[start:end]
        next_cursor = str(end) if end < len(self.media) else None
        return {"items": items, "next_cursor": next_cursor}

    def download_media(self, media_id: str, destination: str) -> Dict[str, Any]:
        item = next((m for m in self.media if m.get("id") == media_id), None)
        if item is None:
            raise ValueError(f"Unknown media id: {media_id}")
        # Stubbed local behavior; a real implementation would stream bytes.
        return {
            "media_id": media_id,
            "destination": destination,
            "bytes_written": item.get("size_bytes", 0),
        }
