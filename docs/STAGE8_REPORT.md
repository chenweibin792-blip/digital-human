# Stage 8 Report: Final Testing

Date: 2026-07-26

Stage 8 passed for the default 720P single-session configuration.

- 29 automated regression tests passed.
- Direct speech, local mock AI, multi-turn history, clear, stop, reconnect,
  refresh, voice settings, rapid send and mobile/desktop flows passed.
- Ten messages passed even with SSE deliberately disabled; status polling
  recovered the UI completion state.
- Three connect/close cycles released all sessions without worker growth.
- Final 30-minute run: 1800.9 seconds, 10 messages, 60 samples, WebRTC connected
  throughout, infer FPS 57.2646, final FPS 24.9543, GPU growth 0 MB, OOM 0,
  clock delta 0.02 seconds and zero browser/request issues.
- Secret, Git-ignore, random-path and temporary-cleanup checks passed.
- Port, missing model, missing FFmpeg and unavailable CUDA failures were
  reported explicitly.

Real-provider API acceptance and deterministic recovery inside the exact same
session remain evidence boundaries. Detailed commands, measurements and known
issues are in `docs/TEST_REPORT.md`.
