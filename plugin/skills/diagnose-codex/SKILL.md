# diagnose-codex

Use this skill when the user asks why Codex is thinking, slow, stuck, waiting, or repeatedly asking for permission.

## Workflow

1. Prefer `codex-doctor notify` for Codex App stuck feedback.
2. Use `codex-doctor notify --after 20` when the user wants faster feedback.
3. Use `codex-doctor diagnose` only for a one-shot debug check.
4. Interpret the state without claiming access to hidden model reasoning.

## Interpretation

- `NETWORK_SUSPECTED`: network, DNS, TLS, proxy, VPN, or firewall may be blocking OpenAI.
- `API_OR_MODEL_WAITING`: network is reachable, but Codex is likely waiting for API/model response.
- `TOOL_RUNNING`: local command is still running.
- `APPROVAL_WAITING`: user approval is needed.
- `CONTEXT_COMPACTING`: Codex is compacting long-session context.
- `SANDBOX_OR_PERMISSION_BLOCKED`: command likely hit sandbox or permission policy.
- `MODEL_STREAMING`: Codex App is actively writing reasoning/search/message events.

## Privacy

Do not ask for API keys, complete prompts, hidden reasoning, or full command output.
