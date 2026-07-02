# Plugin Install

The optional plugin package lives in `plugin/`.

It provides lifecycle hooks and a small `diagnose-codex` skill that points users
to the CLI health check. The CLI remains the main product surface:

```bash
codex-doctor
codex-doctor report
```

Before publishing, add real PNG assets to `plugin/assets/icon.png` and
`plugin/assets/logo.png`.
