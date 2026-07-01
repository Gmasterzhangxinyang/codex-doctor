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
