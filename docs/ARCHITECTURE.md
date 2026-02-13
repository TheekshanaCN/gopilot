# GoPilot Architecture

## 1. Control Plane

- **LLM provider abstraction (`agent/planner.py`)**: switches between Gemini/OpenAI/Claude clients using `LLM_PROVIDER` and `LLM_MODEL`.

- **Planner (`agent/planner.py`)**: turns text input into validated `CameraIntent`.
- **Coach (`agent/coach.py`)**: generates short on-device guidance.
- **Executor (`agent/executor.py`)**: applies mode/shutter commands with retries.

## 2. Camera Plane

- **Command model (`gopro/commands.py`)**: enums and HERO7 endpoint mapping.
- **HTTP client (`gopro/client.py`)**: status/settings/media operations with backoff + circuit breaker.

## 3. Session Plane

- **Session controller (`agent/executor.py:SessionController`)**:
  - state machine: `IDLE -> GUIDING -> READY_TO_SHOOT -> CAPTURING -> REVIEWING`
  - readiness scoring (`framing_score`, `lighting_score`, `motion_score`)
  - JSONL audit logging per session id

## 4. Integration Plane

- **MCP server (`mcp/server.py`)**: strongly typed Pydantic request/response schemas and tools.
- **MCP entrypoint (`mcp/__main__.py`)**: stdio/sse/streamable-http transports.

## 5. Configuration

- `.env` + environment variables via `config.py`
- built-in profiles:
  - `indoor_photo`
  - `outdoor_video`
  - `vlog_walk`
