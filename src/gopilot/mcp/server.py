from __future__ import annotations

from dataclasses import dataclass

from gopilot.agent.executor import CommandExecutor
from gopilot.agent.planner import ShotPlanner
from gopilot.gopro.commands import CameraIntent


@dataclass(frozen=True)
class MCPTool:
    name: str
    description: str


class GoPilotMCPServer:
    def __init__(self, planner: ShotPlanner, executor: CommandExecutor):
        self._planner = planner
        self._executor = executor

    @staticmethod
    def tools() -> list[MCPTool]:
        return [
            MCPTool(
                name="plan_and_execute_shot",
                description="Plan GoPro commands from natural language and execute safely with retries.",
            )
        ]

    def plan_and_execute_shot(self, prompt: str) -> CameraIntent:
        intent = self._planner.plan(prompt)
        self._executor.execute(intent)
        return intent
