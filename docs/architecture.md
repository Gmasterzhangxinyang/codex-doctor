# Architecture

Codex Doctor is a one-shot local health check for visible Codex session state.

It does not run a daemon, watch in the background, or claim access to model
reasoning. The command reads local evidence, classifies the visible state, and
prints a conservative summary.

## Evidence Sources

1. Codex Doctor lifecycle hooks, when installed.
2. Codex App local session metadata, as a best-effort fallback.
3. One OpenAI network probe, unless disabled.
4. Local SQLite/JSONL records written by the hook recorder.

## Flow

```text
CLI
  -> one_shot.py
      -> current_status.py
          -> app_monitor.py
          -> storage.py
          -> state_machine.py
          -> network_probe.py
      -> messages.py
      -> report.py
```

The state machine emits visible states such as `TOOL_RUNNING`,
`APPROVAL_WAITING`, `NETWORK_SUSPECTED`, `API_OR_MODEL_WAITING`, `DONE`, and
`IDLE`.

## Boundary

Codex Doctor reports evidence. It does not decide what the model is thinking.
When evidence is incomplete, output should say that plainly.
