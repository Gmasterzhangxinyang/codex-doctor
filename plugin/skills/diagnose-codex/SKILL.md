# diagnose-codex

Use this skill when the user asks why Codex is thinking, slow, stuck, waiting, or repeatedly asking for permission.

## Workflow

1. Ask the user to run `codex-doctor doctor` if they need an environment/network check.
2. Ask the user to run `codex-doctor watch` for a live dashboard.
3. Ask the user to run `codex-doctor report --last` for a Markdown summary of the latest recorded session.
4. Interpret the state without claiming access to hidden model reasoning.

## Interpretation

- `NETWORK_SUSPECTED`: network, DNS, TLS, proxy, VPN, or firewall may be blocking OpenAI.
- `API_OR_MODEL_WAITING`: network is reachable, but Codex is likely waiting for API/model response.
- `TOOL_RUNNING`: local command is still running.
- `APPROVAL_WAITING`: user approval is needed.
- `CONTEXT_COMPACTING`: Codex is compacting long-session context.
- `SANDBOX_OR_PERMISSION_BLOCKED`: command likely hit sandbox or permission policy.

## Privacy

Do not ask for API keys, complete prompts, hidden reasoning, or full command output. Prefer local report summaries.
