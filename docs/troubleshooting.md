# Troubleshooting

## OpenAI probe returns 401

That is usually good for this tool. It means `api.openai.com` was reachable and
responded. Codex Doctor does not send your API key for probes.

## `--lang` is missing after reinstall

Your shell may be running an old entry point from another Python environment.

```bash
which codex-doctor
codex-doctor --help
codex-doctor install --help
hash -r
python -m pip install -e .
```

You can bypass the console script:

```bash
python -m codex_doctor install --lang zh
python -m codex_doctor
```

## No activity is detected

Run:

```bash
codex-doctor install
```

Then start a new Codex session. If hooks are not available, Codex Doctor will
fall back to safe Codex App session metadata when possible.

## The status feels uncertain

That can happen. Codex Doctor is a visible-evidence health check, not a model
reasoning inspector. Treat `LOW` and `MEDIUM` confidence as prompts to inspect
the recent event list, terminal command state, and network probe result.
