import os
import re
import time
import json
import requests
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ===== CONFIG =====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY. Add it to .env")

GOPRO = {
    "mode": {
        "photo": "http://10.5.5.9/gp/gpControl/command/mode?p=1",
        "video": "http://10.5.5.9/gp/gpControl/command/mode?p=0",
        "timelapse": "http://10.5.5.9/gp/gpControl/command/mode?p=2",
    },
    "shutter": {
        "start": "http://10.5.5.9/gp/gpControl/command/shutter?p=1",
        "stop":  "http://10.5.5.9/gp/gpControl/command/shutter?p=0",
    }
}

# ===== INIT GEMINI =====
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-3-flash-preview",
    system_instruction="""
You are a command parser for a GoPro camera.

Decide:
- mode: photo, video, timelapse
- action: start, stop, none

Return JSON ONLY:
{
  "mode": "photo|video|timelapse",
  "action": "start|stop|none"
}

Rules:
- "take photo", "capture", "shoot" => photo + start
- "record", "take a video", "start video" => video + start
- "stop", "stop recording" => action stop
- "timelapse" => timelapse (+ start if implied)
If unclear, pick the closest.
"""
)

# ===== HELPERS =====
def parse_duration_seconds(text: str) -> int | None:
    t = text.lower().strip()

    # patterns like: 20 sec, 20 seconds, 20s
    m = re.search(r"\b(\d+)\s*(s|sec|secs|second|seconds)\b", t)
    if m:
        return int(m.group(1))

    # patterns like: 1 min, 2 minutes, 1m
    m = re.search(r"\b(\d+)\s*(m|min|mins|minute|minutes)\b", t)
    if m:
        return int(m.group(1)) * 60

    return None

def ask_ai(user_prompt: str) -> dict:
    response = model.generate_content(user_prompt)
    return json.loads(response.text.strip())

def send(url: str) -> None:
    r = requests.get(url, timeout=3)
    if r.status_code != 200:
        raise RuntimeError(f"GoPro command failed: {r.status_code} for {url}")

def execute(ai_result: dict, duration_s: int | None):
    mode = ai_result.get("mode", "video")
    action = ai_result.get("action", "none")

    # Set mode first
    if mode in GOPRO["mode"]:
        send(GOPRO["mode"][mode])
        print(f"🎥 Mode set to {mode.upper()}")

    # Shutter actions
    if action == "start":
        send(GOPRO["shutter"]["start"])
        print("🔴 Shutter START")

        # Auto-stop if duration requested and it makes sense
        if duration_s and duration_s > 0 and mode in ("video", "timelapse"):
            print(f"⏱️ Waiting {duration_s}s then STOP...")
            time.sleep(duration_s)
            send(GOPRO["shutter"]["stop"])
            print("⏹️ Shutter STOP")

    elif action == "stop":
        send(GOPRO["shutter"]["stop"])
        print("⏹️ Shutter STOP")

# ===== MAIN LOOP =====
while True:
    user_input = input("\n🎙️ Say command (or 'exit'): ").strip()
    if user_input.lower() == "exit":
        break

    duration_s = parse_duration_seconds(user_input)

    ai_result = ask_ai(user_input)
    print("🤖 AI decision:", ai_result, "| duration:", duration_s)

    execute(ai_result, duration_s)
