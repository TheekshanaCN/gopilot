from __future__ import annotations

from gopilot.agent.coach import LiveCoach
from gopilot.agent.executor import CommandExecutor
from gopilot.agent.planner import ShotPlanner


class GoPilotApp:
    def __init__(self, planner: ShotPlanner, executor: CommandExecutor, coach: LiveCoach):
        self._planner = planner
        self._executor = executor
        self._coach = coach

    def run(self) -> None:
        while True:
            user_input = input("\n🎙️ Say command (or 'exit'): ").strip()
            if user_input.lower() == "exit":
                break

            intent = self._planner.plan(user_input)
            print("🤖 AI decision:", intent)
            print("🧭 Coach:", self._coach.guidance_for(intent))
            self._executor.execute(intent)
