# MCP Tools Reference

## camera.get_status
Returns mode, capture state, settings map, and media count.

## camera.set_mode
Input:
- `mode`: `photo | video | timelapse`

## camera.start_capture / camera.stop_capture
Starts/stops shutter.

## camera.set_setting
Input:
- `key`: setting id (string)
- `value`: option id (number)

## camera.list_media
Input:
- `limit`: 1..200
- `cursor`: optional pagination cursor

Returns paged media entries with `id`, `filename`, `created_at`, `size_bytes`.

## camera.download_media
Input:
- `media_id`: e.g. `100GOPRO/GX010001.MP4`
- `destination`: output path on local filesystem

## agent.start_autovlogger_session
Input:
- `prompt`: shooting objective
- `mode`: `photo | video | timelapse`

## agent.stop_session
Input:
- optional `session_id`
