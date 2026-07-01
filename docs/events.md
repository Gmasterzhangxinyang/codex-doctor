# Event Model

Codex Doctor normalizes hook and wrapper observations into a small event schema.

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

The schema is intentionally conservative. Tool input is represented as a hash and short redacted snippet. Full prompt content and full command output are not stored by default.

## Primary Hook Events

- `SessionStart`
- `UserPromptSubmit`
- `PreToolUse`
- `PermissionRequest`
- `PostToolUse`
- `PreCompact`
- `PostCompact`
- `Stop`

## Wrapper Events

- `TerminalOutput`
- `SessionStart`
- `Stop`

Wrapper events help distinguish silent model/API waiting from active local terminal work.
