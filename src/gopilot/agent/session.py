from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class AutovloggerAgent:
    active_session_id: Optional[str] = None

    def start_autovlogger_session(self, prompt: str, mode: str = "video") -> Dict[str, Any]:
        if self.active_session_id:
            return {
                "session_id": self.active_session_id,
                "started": False,
                "message": "Session already active",
            }
        self.active_session_id = str(uuid.uuid4())
        return {
            "session_id": self.active_session_id,
            "started": True,
            "mode": mode,
            "prompt": prompt,
        }

    def stop_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.active_session_id:
            return {"stopped": False, "message": "No active session"}
        if session_id and session_id != self.active_session_id:
            return {
                "stopped": False,
                "message": "session_id does not match active session",
                "active_session_id": self.active_session_id,
            }
        stopped_id = self.active_session_id
        self.active_session_id = None
        return {"stopped": True, "session_id": stopped_id}
