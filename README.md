# GoPilot

GoPilot is an AI-assisted GoPro control agent with:

- Natural-language shot planning (`ShotPlanner`)
- Reliable camera control with retries + circuit breaker (`GoProClient`)
- Auto-vlogger session controller with guidance loop (`SessionController`)
- MCP server for external orchestration (`gopilot.mcp`)
- Multi-LLM support (`gemini`, `openai`, `claude`) with selectable model

## Project Structure

- `src/gopilot/gopro/`: HERO7 command mapping + HTTP client
- `src/gopilot/agent/`: planner, coaching, execution, autonomous session flow
- `src/gopilot/mcp/`: MCP server and tool registration
- `src/gopilot/config.py`: env-based config and profile presets
- `tests/`: unit and integration-stub tests

## Quick Start

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables (examples):

   ```bash
   export GOPRO_HOST="10.5.5.9"
   export GOPRO_PROFILE="outdoor_video"
   
   # Choose ONE provider:
   export LLM_PROVIDER="gemini"
   export GEMINI_API_KEY="your_key"
   export LLM_MODEL="gemini-1.5-flash"

   # or
   export LLM_PROVIDER="openai"
   export OPENAI_API_KEY="your_key"
   export LLM_MODEL="gpt-4o-mini"

   # or
   export LLM_PROVIDER="claude"
   export ANTHROPIC_API_KEY="your_key"
   export LLM_MODEL="claude-3-5-sonnet-20241022"
   ```

3. Run CLI app:

   ```bash
   PYTHONPATH=src python -m gopilot.main
   ```

4. Run MCP server:

   ```bash
   PYTHONPATH=src python -m gopilot.mcp --transport stdio
   ```

## MCP Tools

- `camera.get_status`
- `camera.set_mode`
- `camera.start_capture`
- `camera.stop_capture`
- `camera.set_setting`
- `camera.list_media`
- `camera.download_media`
- `agent.start_autovlogger_session`
- `agent.stop_session`

See `docs/MCP_TOOLS.md` for request/response shape.

## Testing

```bash
PYTHONPATH=src pytest -q
```
