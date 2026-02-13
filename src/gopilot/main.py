from __future__ import annotations

from gopilot.agent.coach import LiveCoach
from gopilot.agent.executor import CommandExecutor
from gopilot.agent.planner import ShotPlanner
from gopilot.app import GoPilotApp
from gopilot.config import load_config
from gopilot.gopro.client import GoProClient
from gopilot.logging import configure_logging


def main() -> None:
    configure_logging()
    config = load_config()
    app = GoPilotApp(
        planner=ShotPlanner(config.gemini),
        executor=CommandExecutor(GoProClient(config.gopro)),
        coach=LiveCoach(),
    )
    app.run()


if __name__ == "__main__":
    main()
