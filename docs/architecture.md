# Architecture

Codex Doctor combines four observable signals:

1. Codex lifecycle hooks.
2. PTY wrapper output activity.
3. Local process tree samples.
4. OpenAI network probes.

The state machine classifies those signals into human-readable states such as `TOOL_RUNNING`, `APPROVAL_WAITING`, `NETWORK_SUSPECTED`, and `API_OR_MODEL_WAITING`.

The project deliberately avoids Codex internals and hidden chain-of-thought. It records local operational evidence only.
