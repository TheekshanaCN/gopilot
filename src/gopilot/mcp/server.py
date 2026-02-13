from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from gopilot.agent.session import AutovloggerAgent
from gopilot.gopro.client import GoProClient


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmptyInput(StrictModel):
    pass


class CameraStatusOutput(StrictModel):
    mode: Literal["photo", "video", "timelapse"]
    capture_state: Literal["idle", "capturing"]
    settings: Dict[str, Any]
    media_count: int


class CameraSetModeInput(StrictModel):
    mode: Literal["photo", "video", "timelapse"]


class CameraSetModeOutput(StrictModel):
    mode: Literal["photo", "video", "timelapse"]


class CaptureOutput(StrictModel):
    capture_state: Literal["idle", "capturing"]


class CameraSettingInput(StrictModel):
    key: str = Field(min_length=1)
    value: Any


class CameraSettingOutput(StrictModel):
    key: str
    value: Any


class CameraListMediaInput(StrictModel):
    limit: int = Field(default=50, ge=1, le=200)
    cursor: Optional[str] = None


class MediaItem(StrictModel):
    id: str
    filename: str
    created_at: str
    size_bytes: int


class CameraListMediaOutput(StrictModel):
    items: List[MediaItem]
    next_cursor: Optional[str] = None


class CameraDownloadMediaInput(StrictModel):
    media_id: str = Field(min_length=1)
    destination: str = Field(min_length=1)


class CameraDownloadMediaOutput(StrictModel):
    media_id: str
    destination: str
    bytes_written: int


class AgentStartSessionInput(StrictModel):
    prompt: str = Field(min_length=1)
    mode: Literal["photo", "video", "timelapse"] = "video"


class AgentStartSessionOutput(StrictModel):
    session_id: str
    started: bool
    message: Optional[str] = None
    mode: Optional[str] = None
    prompt: Optional[str] = None


class AgentStopSessionInput(StrictModel):
    session_id: Optional[str] = None


class AgentStopSessionOutput(StrictModel):
    stopped: bool
    message: Optional[str] = None
    session_id: Optional[str] = None
    active_session_id: Optional[str] = None


class GoPilotMCPServer:
    def __init__(self, client: Optional[GoProClient] = None, agent: Optional[AutovloggerAgent] = None):
        self.client = client or GoProClient()
        self.agent = agent or AutovloggerAgent()
        self.mcp = FastMCP(name="gopilot")
        self._register_tools()

    def _register_tools(self) -> None:
        @self.mcp.tool(name="camera.get_status", description="Get the current camera status")
        def camera_get_status(_args: EmptyInput) -> CameraStatusOutput:
            return CameraStatusOutput(**self.client.get_status())

        @self.mcp.tool(name="camera.set_mode", description="Set camera mode")
        def camera_set_mode(args: CameraSetModeInput) -> CameraSetModeOutput:
            return CameraSetModeOutput(**self.client.set_mode(args.mode))

        @self.mcp.tool(name="camera.start_capture", description="Start shutter capture")
        def camera_start_capture(_args: EmptyInput) -> CaptureOutput:
            return CaptureOutput(**self.client.start_capture())

        @self.mcp.tool(name="camera.stop_capture", description="Stop shutter capture")
        def camera_stop_capture(_args: EmptyInput) -> CaptureOutput:
            return CaptureOutput(**self.client.stop_capture())

        @self.mcp.tool(name="camera.set_setting", description="Set a camera setting")
        def camera_set_setting(args: CameraSettingInput) -> CameraSettingOutput:
            return CameraSettingOutput(**self.client.set_setting(args.key, args.value))

        @self.mcp.tool(name="camera.list_media", description="List media files on camera")
        def camera_list_media(args: CameraListMediaInput) -> CameraListMediaOutput:
            result = self.client.list_media(limit=args.limit, cursor=args.cursor)
            return CameraListMediaOutput(**result)

        @self.mcp.tool(name="camera.download_media", description="Download media by id")
        def camera_download_media(args: CameraDownloadMediaInput) -> CameraDownloadMediaOutput:
            return CameraDownloadMediaOutput(
                **self.client.download_media(args.media_id, args.destination)
            )

        @self.mcp.tool(
            name="agent.start_autovlogger_session",
            description="Start an automated vlogging session",
        )
        def agent_start_autovlogger_session(args: AgentStartSessionInput) -> AgentStartSessionOutput:
            return AgentStartSessionOutput(
                **self.agent.start_autovlogger_session(prompt=args.prompt, mode=args.mode)
            )

        @self.mcp.tool(name="agent.stop_session", description="Stop current autovlogger session")
        def agent_stop_session(args: AgentStopSessionInput) -> AgentStopSessionOutput:
            return AgentStopSessionOutput(**self.agent.stop_session(session_id=args.session_id))


def build_server(client: Optional[GoProClient] = None, agent: Optional[AutovloggerAgent] = None) -> FastMCP:
    return GoPilotMCPServer(client=client, agent=agent).mcp
