from __future__ import annotations

from gopilot.gopro.commands import CameraAction, CameraIntent, CameraMode


class LiveCoach:
    def guidance_for(self, intent: CameraIntent) -> str:
        if intent.mode == CameraMode.PHOTO and intent.action == CameraAction.START:
            return "Hold steady, adjust lighting, and tap shutter when your frame is clean."
        if intent.mode == CameraMode.VIDEO and intent.action == CameraAction.START:
            return "Move slowly forward, keep horizon level, and avoid sudden pans."
        if intent.mode == CameraMode.TIMELAPSE and intent.action == CameraAction.START:
            return "Stabilize the camera and avoid touching it during capture."
        if intent.action == CameraAction.STOP:
            return "Capture stopped. Review framing and prepare for the next shot."
        return "Ready for your next command."
