# Changelog

## 0.1.0

- Initial MVP scaffold for Codex Doctor.
- Added local event storage, hook recorder, state machine, network probe, process monitor, watch dashboard, report generation, and Codex plugin package.

## 0.1.1

- Detect the Codex executable bundled inside macOS Codex.app when `codex` is not on `PATH`.
- Fall back to a temporary data directory when the platform data directory is not writable.

## 0.1.2

- Add a conservative Codex App rollout fallback for `codex-doctor watch`.
- Show App activity from local event metadata when hooks are not emitted by Codex App sessions.

## 0.1.3

- Keep `codex-doctor watch` running when the local Codex Doctor SQLite database is temporarily unavailable.
- Continue showing Codex App fallback activity when hook/wrapper storage cannot be opened.

## 0.3.5

- Include the Codex App project name in stuck notifications.
- Show the full detected project path in `codex-doctor diagnose`.

## 0.3.4

- Make `codex-doctor notify` prompt for language and stuck threshold seconds when options are not provided.
- Keep `--lang zh|en` and `--after <seconds>` for users who want to skip the startup choices.

## 0.3.3

- Add Chinese stuck feedback with current situation, likely blockage reason, and suggested next step.
- Use the Chinese feedback in notifications and one-shot diagnosis output.

## 0.3.2

- Make `codex-doctor install` verify macOS notification delivery by default.
- Fail installation when notifications are unavailable, with an explicit `--skip-notification-check` escape hatch for headless environments.

## 0.3.1

- Add `codex-doctor notify --test` to verify whether macOS notifications are actually available.
- Report notification delivery failures instead of treating failed `osascript` calls as success.

## 0.3.0

- Add `codex-doctor notify` as the focused Codex App stuck-feedback command.
- Reposition dashboard and wrapper commands as advanced/debug workflows.

## 0.2.2

- Make `codex-doctor monitor --notify` send stuck feedback when active states persist too long.
- Add `--stuck-after` to tune the stuck feedback threshold.

## 0.2.1

- Add `codex-doctor monitor --notify --notify-all` for users who want notifications on normal Codex App activity changes, not only stuck/error states.

## 0.2.0

- Add `codex-doctor diagnose` as the primary Codex App-friendly one-shot diagnosis command.
- Add `codex-doctor monitor --notify` for lightweight polling and macOS notifications.
- Combine Codex App rollout metadata with OpenAI network probes to distinguish stale App activity from network/API waiting.
