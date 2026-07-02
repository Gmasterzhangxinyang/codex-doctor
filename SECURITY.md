# Security Policy

## Supported Versions

Codex Doctor is pre-1.0. Security fixes target the latest released version and the default branch.

## Reporting a Vulnerability

Please report vulnerabilities privately through GitHub Security Advisories:

https://github.com/Gmasterzhangxinyang/codex-doctor/security/advisories/new

Please do not open public issues containing secrets, private prompts, command output, or exploit details.

## Security Model

Codex Doctor is local-first and should not upload user prompts, code, command output, API keys, reports, or local session evidence.

Expected behavior:

- Hooks must fail closed and exit 0 so they do not break Codex.
- Network probes must not send API keys.
- Health summaries and reports must be generated locally.
- Secret-looking fields must be redacted.
- Hidden model reasoning must never be requested, inferred as content, or displayed.
