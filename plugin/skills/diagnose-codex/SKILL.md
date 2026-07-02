# diagnose-codex

Use this skill when the user asks for a local health check of a Codex session:
slow output, possible waiting, approval prompts, network uncertainty, or local
tool activity.

## Workflow

1. Prefer `codex-doctor` for the default one-shot health check.
2. Use `codex-doctor report` when the user wants a slightly more report-like
   terminal summary.
3. Use `--lang zh` or `--lang en` when the user wants an explicit language.
4. Interpret output as visible evidence only. Do not claim access to hidden model
   reasoning.

## Interpretation

- `NETWORK_SUSPECTED`: network, DNS, TLS, proxy, VPN, or firewall may be blocking OpenAI.
- `API_OR_MODEL_WAITING`: network is reachable; visible evidence suggests API/model waiting or reconnect.
- `TOOL_RUNNING`: local events show tool calls without matching completion output.
- `APPROVAL_WAITING`: local events show a permission request without later progress.
- `CONTEXT_COMPACTING`: local events show context compaction started.
- `SANDBOX_OR_PERMISSION_BLOCKED`: tool output contains sandbox or permission errors.
- `MODEL_STREAMING`: Codex App is writing visible reasoning/search/message event metadata.

## Privacy

Do not ask for API keys, complete prompts, hidden reasoning, or full command
output. If evidence is incomplete, say so directly.
