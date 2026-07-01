# Changelog

## 0.1.0

- Initial MVP scaffold for Codex Doctor.
- Added local event storage, hook recorder, state machine, network probe, process monitor, watch dashboard, report generation, and Codex plugin package.

## 0.1.1

- Detect the Codex executable bundled inside macOS Codex.app when `codex` is not on `PATH`.
- Fall back to a temporary data directory when the platform data directory is not writable.
