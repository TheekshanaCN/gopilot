from __future__ import annotations

from gopilot.agent.coach import LiveCoach
from gopilot.agent.executor import CommandExecutor
from gopilot.agent.planner import ShotPlanner
from gopilot.config import load_config
from gopilot.gopro.client import GoProClient


def main() -> None:
    config = load_config()
    planner = ShotPlanner(config.gemini)
    executor = CommandExecutor(GoProClient(config.gopro))
    coach = LiveCoach()

    while True:
        user_input = input("\n🎙️ Say command (or 'exit'): ").strip()
        if user_input.lower() == "exit":
            break

        intent = planner.plan(user_input)
        print("🤖 AI decision:", intent)
        print("🧭 Coach:", coach.guidance_for(intent))
        executor.execute(intent)


if __name__ == "__main__":
    main()
