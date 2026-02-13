from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol

from gopilot.gopro.client import GoProClient
from gopilot.gopro.commands import CameraAction, CameraIntent, CameraMode


class CommandExecutor:
    def __init__(self, client: GoProClient, retries: int = 2, retry_delay_s: float = 0.5):
        self._client = client
        self._retries = retries
        self._retry_delay_s = retry_delay_s

    @property
    def client(self) -> GoProClient:
        return self._client

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


class SessionState(str, Enum):
    IDLE = "idle"
    GUIDING = "guiding"
    READY_TO_SHOOT = "ready_to_shoot"
    CAPTURING = "capturing"
    REVIEWING = "reviewing"


@dataclass(frozen=True)
class CaptureThresholds:
    min_framing_score: float = 0.75
    min_lighting_score: float = 0.7
    max_motion_score: float = 0.35


@dataclass
class SessionContext:
    prompt: str
    mode: CameraMode = CameraMode.VIDEO
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: SessionState = SessionState.IDLE
    cycle: int = 0
    capture_count: int = 0


class Planner(Protocol):
    def plan(self, user_prompt: str) -> CameraIntent:
        ...


class Coach(Protocol):
    def guidance_for(self, intent: CameraIntent) -> str:
        ...


class SessionController:
    def __init__(
        self,
        planner: Planner,
        coach: Coach,
        executor: CommandExecutor,
        *,
        thresholds: CaptureThresholds | None = None,
        logs_dir: str | Path = "session_logs",
        sleep_s: float = 0.25,
    ):
        self._planner = planner
        self._coach = coach
        self._executor = executor
        self._thresholds = thresholds or CaptureThresholds()
        self._logs_dir = Path(logs_dir)
        self._sleep_s = sleep_s
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def run(
        self,
        prompt: str,
        *,
        mode: CameraMode = CameraMode.VIDEO,
        max_cycles: int = 20,
        context_provider: Callable[[SessionContext], dict[str, Any]] | None = None,
        stop_criteria: Callable[[SessionContext, dict[str, Any]], bool] | None = None,
    ) -> SessionContext:
        session = SessionContext(prompt=prompt, mode=mode)
        self._stop_requested = False
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._logs_dir / f"{session.session_id}.jsonl"

        while session.cycle < max_cycles and not self._stop_requested:
            session.cycle += 1
            camera_status = self._executor.client.get_status()
            scene_context = context_provider(session) if context_provider else {}

            if stop_criteria and stop_criteria(session, scene_context):
                break
            if bool(scene_context.get("stop_session")):
                break

            session.state = SessionState.GUIDING
            intent = self._planner.plan(self._planner_prompt(session, camera_status, scene_context))
            guidance = self._coach.guidance_for(intent)

            self._emit_guidance(guidance)

            ready = self._is_ready_to_capture(scene_context)
            if intent.action == CameraAction.START and ready:
                session.state = SessionState.READY_TO_SHOOT
                self._write_log(log_path, session, camera_status, scene_context, intent, guidance)

                session.state = SessionState.CAPTURING
                self._executor.execute(intent)
                session.capture_count += 1

                session.state = SessionState.REVIEWING
            elif intent.mode != CameraMode(camera_status.get("mode", CameraMode.VIDEO.value)):
                self._executor.execute(CameraIntent(mode=intent.mode, action=CameraAction.NONE))

            self._write_log(log_path, session, camera_status, scene_context, intent, guidance)
            time.sleep(self._sleep_s)

        session.state = SessionState.IDLE
        self._write_log(log_path, session, {"capture_state": "idle"}, {"ended": True}, None, "Session ended")
        return session

    def _planner_prompt(
        self,
        session: SessionContext,
        camera_status: dict[str, Any],
        scene_context: dict[str, Any],
    ) -> str:
        payload = {
            "session_id": session.session_id,
            "cycle": session.cycle,
            "request": session.prompt,
            "target_mode": session.mode.value,
            "camera_status": camera_status,
            "scene_context": scene_context,
            "expected_actions": ["coach_prompt", "capture", "setting_change"],
        }
        return json.dumps(payload)

    def _is_ready_to_capture(self, scene_context: dict[str, Any]) -> bool:
        framing = float(scene_context.get("framing_score", 0.0))
        lighting = float(scene_context.get("lighting_score", 0.0))
        motion = float(scene_context.get("motion_score", 1.0))
        return (
            framing >= self._thresholds.min_framing_score
            and lighting >= self._thresholds.min_lighting_score
            and motion <= self._thresholds.max_motion_score
        )

    @staticmethod
    def _emit_guidance(message: str) -> None:
        print(f"🧭 Coach: {message}")

    def _write_log(
        self,
        path: Path,
        session: SessionContext,
        camera_status: dict[str, Any],
        scene_context: dict[str, Any],
        intent: CameraIntent | None,
        guidance: str,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session": {
                **asdict(session),
                "mode": session.mode.value,
                "state": session.state.value,
            },
            "camera_status": camera_status,
            "scene_context": scene_context,
            "intent": asdict(intent) if intent else None,
            "guidance": guidance,
        }
        if entry["intent"]:
            entry["intent"]["mode"] = intent.mode.value
            entry["intent"]["action"] = intent.action.value
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
