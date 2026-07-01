# Troubleshooting

## OpenAI probe returns 401

That is usually good for this tool. It means `api.openai.com` was reachable and responded. Codex Doctor does not send your API key for probes.

## `codex-doctor run` cannot find Codex

Make sure the `codex` executable is on your `PATH`.

## Hooks do not appear

Run:

```bash
codex-doctor install
```

Then start a new Codex session.
