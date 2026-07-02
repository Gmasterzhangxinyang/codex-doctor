# Event Model

Codex Doctor stores a small redacted event schema for local health checks.

```text
Event
  id
  ts
  source
  session_id
  turn_id
  event_type
  cwd
  model
  permission_mode
  tool_name
  tool_input_hash
  tool_input_snippet
  success
  duration_ms
  raw_redacted
```

The schema is intentionally conservative. Tool input is stored as a hash and a
short redacted snippet. Full prompts and full command output are not stored by
default.

## Hook Events

- `SessionStart`
- `UserPromptSubmit`
- `PreToolUse`
- `PermissionRequest`
- `PostToolUse`
- `PreCompact`
- `PostCompact`
- `Stop`

## App Metadata

When hooks are unavailable, Codex Doctor reads safe event metadata from local
Codex App session files, such as event type, timestamp, tool name, status, and
call id. It does not read hidden reasoning as content.
