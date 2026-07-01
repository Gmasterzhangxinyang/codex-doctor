# Contributing

Thanks for taking a look at Codex Doctor.

This project has one hard boundary: it diagnoses observable runtime state only. It must not attempt to reveal hidden model reasoning, intercept API keys, upload private data, or persist full prompts and command output by default.

## Development

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
```

Useful commands:

```bash
codex-doctor doctor
codex-doctor report --last
codex-doctor run -- --help
```

## Pull Requests

Good PRs usually include:

- A clear user-facing diagnostic improvement.
- Tests for state-machine, redaction, storage, or reporting changes.
- No new cloud dependency.
- No logging of secrets, complete prompts, or complete tool output.

## Design Principles

- Local-first by default.
- Fast hooks that never break Codex.
- Confidence labels for every diagnosis.
- Observable evidence over speculation.
- Simple code paths over clever abstractions.
