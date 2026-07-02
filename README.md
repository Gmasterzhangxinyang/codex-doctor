# Codex Doctor

[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Local First](https://img.shields.io/badge/privacy-local--first-10A37F)](docs/privacy.md)
[![Status](https://img.shields.io/badge/status-alpha-orange)](CHANGELOG.md)

![Codex Doctor banner](docs/assets/banner.svg)

Check visible Codex session health from your terminal.

Codex Doctor is a small, local-first health-check CLI for Codex sessions. It does
not run a daemon, poll in the background, or upload data. When Codex feels stuck,
run one command to see the latest visible evidence: recent event age, tool calls,
network probe result, approval hints, sandbox errors, and a conservative possible
explanation.

Codex Doctor only reports observable runtime state. It never tries to reveal
hidden model reasoning, and it avoids pretending to know what the model is
thinking.

## Quick Start

```bash
pipx install codex-doctor
codex-doctor install
```

When Codex looks stuck:

```bash
codex-doctor
```

Terminal output is intentionally direct:

```text
可见状态: TOOL_RUNNING
可信度: MEDIUM
可见线索: 可见事件显示 Codex 进入过本地工具阶段。
可能解释: 检测到工具 exec_command 已经启动，还有 2 个工具调用没看到完成输出。
下一步: 检查对应终端/命令是否还在运行；如果已结束，可能是日志事件尚未完整写入。

证据:
- 距最近线索: 8s
- 工具: exec_command
- 未见完成输出的工具调用: 2
```

## What It Answers

Codex Doctor is useful for quick health-check questions like:

- Has the latest visible event stopped updating?
- Is the local command or tool still running?
- Is there a permission approval waiting in the UI?
- Did a sandbox or filesystem permission block the task?
- Is the OpenAI endpoint unreachable because of DNS, proxy, VPN, TLS, or network trouble?
- What visible evidence supports the current status?

It does not explain hidden chain-of-thought. The output is a conservative summary
of local events, tool status, session metadata, and a one-time network probe.

## Install

Recommended:

```bash
pipx install codex-doctor
codex-doctor install
```

During install, choose the default output language:

```text
1. 中文
2. English
选择语言 / Choose language [1/2/zh/en]
```

Non-interactive install:

```bash
codex-doctor install --lang zh
codex-doctor install --lang en
```

Local development:

```bash
git clone https://github.com/Gmasterzhangxinyang/codex-doctor.git
cd codex-doctor
python -m pip install -e ".[dev]"
```

## Usage

Run the default one-shot health check:

```bash
codex-doctor
```

Use the explicit command form:

```bash
codex-doctor diagnose
```

Print a concise terminal report:

```bash
codex-doctor report
```

Write a Markdown report only when you ask for a file:

```bash
codex-doctor report -o codex-report.md
codex-doctor diagnose -o codex-report.md
```

Override language for one run:

```bash
codex-doctor diagnose --lang zh
codex-doctor diagnose --lang en
codex-doctor report --lang zh
codex-doctor report --lang en
```

Skip the network probe when you only want local evidence:

```bash
codex-doctor --no-network
codex-doctor report --no-network
```

Check the local setup:

```bash
codex-doctor doctor
```

## Install Troubleshooting

If `codex-doctor install --lang zh` says `No such option: --lang`, or
`codex-doctor` says `Missing command`, your shell is probably running an older
entry point from another Python environment.

Check what is being executed:

```bash
which codex-doctor
codex-doctor --help
codex-doctor install --help
```

Refresh the shell command cache and reinstall from this checkout:

```bash
hash -r
python -m pip install -e .
```

You can also run the module entry point directly:

```bash
python -m codex_doctor install --lang zh
python -m codex_doctor
```

## Commands

| Command | Purpose |
|---|---|
| `codex-doctor install` | Install lightweight hooks and choose default language. |
| `codex-doctor` | Run the default one-shot health check. |
| `codex-doctor diagnose` | Same health check with explicit options. |
| `codex-doctor report` | Print a concise terminal report, or write Markdown with `-o`. |
| `codex-doctor doctor` | Check Codex CLI, hooks, data directory, and network reachability. |
| `codex-doctor uninstall` | Remove installed hooks. |

## Diagnosis States

| State | Meaning |
|---|---|
| `NETWORK_SUSPECTED` | DNS, TCP, TLS, proxy, VPN, firewall, or routing may be blocking access. |
| `API_OR_MODEL_WAITING` | Network is reachable; Codex is likely waiting on API/model response or reconnect. |
| `TOOL_RUNNING` | Codex appears to be waiting for a local command or tool to finish. |
| `APPROVAL_WAITING` | Codex likely needs a permission approval before continuing. |
| `CONTEXT_COMPACTING` | Codex is processing or compacting long-session context. |
| `SANDBOX_OR_PERMISSION_BLOCKED` | A command likely hit sandbox or filesystem permissions. |
| `DONE` | The latest visible session appears finished. |
| `IDLE` | No recent Codex activity was found. |

Each status includes a confidence level: `HIGH`, `MEDIUM`, or `LOW`. Treat it as a local evidence summary, not ground truth about model reasoning.

## Architecture

Codex Doctor is intentionally small:

```text
codex_doctor/
  cli.py              CLI commands and language selection
  one_shot.py         one-shot health-check/report orchestration
  current_status.py   combines local evidence into current status
  app_monitor.py      reads safe Codex App session metadata
  hook_recorder.py    records redacted hook events
  state_machine.py    classifies observable state
  network_probe.py    curl-first OpenAI connectivity probe
  messages.py         human-readable zh/en explanations
  report.py           optional Markdown report generation
  storage.py          local SQLite + JSONL storage
  redaction.py        sensitive-content redaction
```

The core flow:

1. Read safe local evidence from Codex App metadata and Codex Doctor hooks.
2. Redact sensitive content before storage.
3. Classify the visible state with a small state machine.
4. Run one OpenAI network probe unless disabled.
5. Print a terminal health summary or write a Markdown report.

No daemon. No polling loop. No background alerts. No cloud upload.

## Privacy And Safety

Codex Doctor is built around one rule: diagnose only what is observable.

- No hidden chain-of-thought access.
- No cloud upload.
- No API key interception.
- No network request from hooks.
- No prompt replay.
- Prompt/tool content is redacted and truncated.
- Network probes do not send credentials.
- Data stays in the local user data directory unless you remove it.

See [Privacy](docs/privacy.md) and [Security](SECURITY.md).

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

Useful local checks:

```bash
python -m compileall codex_doctor tests
codex-doctor --no-network
codex-doctor report --no-network
```

## Contributing

Contributions are welcome. Good first areas:

- More precise state-machine tests.
- Additional redaction fixtures.
- Better network error classification.
- Clearer Chinese and English diagnosis messages.
- Docs improvements and real-world troubleshooting examples.

Please keep changes aligned with the privacy boundary: no hidden reasoning, no
cloud upload, and no long-running background process in the main product path.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening larger changes.

## Uninstall

```bash
codex-doctor uninstall
```

Remove local data too:

```bash
codex-doctor uninstall --purge-data
```

## License

MIT. See [LICENSE](LICENSE).
