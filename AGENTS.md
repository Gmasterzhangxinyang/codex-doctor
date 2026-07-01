# AGENTS.md

## Project Goal

Build `codex-doctor`, a local-first diagnostic CLI for Codex CLI. The tool diagnoses why Codex appears to be thinking or stuck.

## Core Principle

Do not attempt to reveal hidden model reasoning. Diagnose observable runtime state only.

## MVP Scope

Implement:

1. CLI commands:
   - install
   - run
   - watch
   - report
   - doctor
   - uninstall

2. Hook recorder:
   - read JSON from stdin
   - redact sensitive content
   - write event to SQLite and JSONL

3. State machine:
   - classify current state
   - emit diagnosis with confidence

4. Network probe:
   - prefer curl
   - fallback to Python socket/httpx
   - classify DNS/connect/TLS/TTFB problems

5. Process monitor:
   - monitor Codex process tree in wrapper mode

6. TUI:
   - render current state and last events with Rich

7. Report:
   - generate Markdown summary

## Quality Bar

- All hook handlers must exit quickly and never break Codex.
- No cloud upload.
- No hidden chain-of-thought access or display.
- Tests for state machine and redaction are required.
- Keep code simple and readable.
