# Privacy

Codex Doctor is local-first.

- No cloud upload.
- No API key interception.
- No hidden model reasoning access.
- Prompt and tool content are redacted and truncated by default.
- Secret-looking fields are replaced with `[REDACTED]`.
- Tool input is stored as a snippet plus SHA-256 hash.

Use `codex-doctor uninstall --purge-data` to remove local history.
