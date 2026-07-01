# Codex Doctor

[![CI](https://github.com/Gmasterzhangxinyang/codex-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/Gmasterzhangxinyang/codex-doctor/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Local First](https://img.shields.io/badge/privacy-local--first-10A37F)](docs/privacy.md)

![Codex Doctor banner](docs/assets/banner.svg)

Know why Codex is thinking.

Codex Doctor is a local-first diagnostic CLI for Codex. It explains whether a slow or stuck Codex session is waiting on network, API/model latency, approval, local tools, context compaction, sandbox policy, or a long-running command.

It does not read or reveal hidden model reasoning. It diagnoses observable runtime state only.

## Why This Exists

Sometimes Codex keeps showing `thinking` and the user has no idea what is happening.

Codex Doctor turns that vague state into a concrete diagnosis:

```text
Codex is running pytest, elapsed 7m32s, CPU 91%.
This is not a network issue.
```

or:

```text
Network looks healthy. api.openai.com returned 401 in 0.44s.
Codex is likely waiting for API/model response.
```

or:

```text
Codex is waiting for your approval.
Check the Codex UI for a permission prompt.
```

## Features

- One-shot Codex App diagnosis with `codex-doctor diagnose`.
- Lightweight monitor with optional macOS notifications via `codex-doctor monitor --notify`.
- Debug dashboard with `codex-doctor watch`.
- PTY wrapper mode with `codex-doctor run`.
- Hook recorder for Codex lifecycle events.
- Best-effort Codex App fallback that reads local rollout event metadata when hooks are not emitted.
- curl-first OpenAI network probe with Python fallback.
- Process-tree sampling with CPU, memory, and child process visibility.
- SQLite plus JSONL local storage.
- Markdown session reports.
- Optional Codex plugin package.
- Privacy-first redaction for prompt/tool data.
- Confidence labels for every diagnosis.

## Install

```bash
pipx install codex-doctor
codex-doctor install
```

For local development:

```bash
git clone https://github.com/Gmasterzhangxinyang/codex-doctor.git
cd codex-doctor
python -m pip install -e ".[dev]"
```

## Quick Start

For Codex App users, start with a one-shot diagnosis:

```bash
codex-doctor diagnose
```

Keep a lightweight monitor running and notify when Codex looks stuck:

```bash
codex-doctor monitor --notify
```

Run Codex through the wrapper when you want the most complete local evidence:

```bash
codex-doctor run
```

Pass Codex arguments after `--`:

```bash
codex-doctor run -- --model gpt-5.5
codex-doctor run -- exec "fix this bug"
```

Or keep using Codex directly and watch recorded hooks:

```bash
codex
codex-doctor watch
```

Generate a report:

```bash
codex-doctor report --last
codex-doctor report --last --output report.md
```

Check the local environment and OpenAI connectivity:

```bash
codex-doctor doctor
```

## Dashboard Preview

```text
┌ Codex Doctor ─────────────────────────────────────────┐
│ Session: 20260701-143812                              │
│ Status: TOOL_RUNNING                                  │
│ Confidence: HIGH                                      │
│                                                        │
│ Diagnosis: Codex is waiting for a local tool to finish │
│ Network: OK HTTP=401                                  │
│ Process: CPU=91.0 MEM=1228.4MB children=3             │
│                                                        │
│ Last events:                                           │
│ 14:38:12 UserPromptSubmit                              │
│ 14:38:44 PreToolUse Bash                               │
└────────────────────────────────────────────────────────┘
```

## Diagnosis States

| State | Meaning |
|---|---|
| `NETWORK_SUSPECTED` | DNS, TCP, TLS, proxy, VPN, or firewall may be blocking the request. |
| `API_OR_MODEL_WAITING` | Network is reachable; Codex is likely waiting on API/model response. |
| `TOOL_RUNNING` | Codex is waiting for a local command or tool to finish. |
| `APPROVAL_WAITING` | Codex needs user approval before continuing. |
| `CONTEXT_COMPACTING` | Codex is compacting long-session context. |
| `SANDBOX_OR_PERMISSION_BLOCKED` | A command likely hit sandbox or permission policy. |
| `DONE` | The session stopped normally. |
| `ERROR` | The session ended with an error signal. |

Every diagnosis includes confidence: `HIGH`, `MEDIUM`, or `LOW`.

## How It Works

Codex Doctor combines four local evidence sources:

1. Codex lifecycle hooks.
2. PTY wrapper terminal activity.
3. Local process-tree samples.
4. OpenAI network probes.

Those signals feed a small state machine that emits a current diagnosis and a reportable timeline.
When Codex App does not emit hooks for a visible App session, `watch` can fall back to the latest local rollout file and display only safe event metadata such as `reasoning`, `function_call`, and `function_call_output`.

See [Architecture](docs/architecture.md) and [Event Model](docs/events.md).

## Privacy Model

Codex Doctor is local-first.

- No cloud upload.
- No API key interception.
- No hidden chain-of-thought access.
- No network request from hooks.
- OpenAI probes do not send credentials.
- Prompt and tool content are redacted and truncated by default.
- Tool input is stored as a small snippet plus SHA-256 hash.

See [Privacy](docs/privacy.md) and [Security Policy](SECURITY.md).

## Commands

```bash
codex-doctor install
codex-doctor diagnose
codex-doctor monitor --notify
codex-doctor run
codex-doctor watch
codex-doctor report --last
codex-doctor doctor
codex-doctor uninstall
```

## Optional Codex Plugin

The optional plugin package lives in [`plugin/`](plugin/). It provides lifecycle hooks and a `diagnose-codex` skill. The CLI remains responsible for `diagnose`, `monitor`, reports, and richer diagnostics.

See [Plugin Install](docs/plugin-install.md).

## Development

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
python -m build
```

## Roadmap

See [Roadmap](docs/roadmap.md).

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md), especially the privacy and safety boundaries.

## Uninstall

```bash
codex-doctor uninstall
```

Historical data is kept unless explicitly purged:

```bash
codex-doctor uninstall --purge-data
```

## License

MIT. See [LICENSE](LICENSE).
