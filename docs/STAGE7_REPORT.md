# Stage 7 Report: Performance Optimization

Date: 2026-07-26

Stage 7 passed for the default 720P profile.

Implemented:

- 720 x 960 portrait default profile at 25 FPS
- Explicit 1080 x 1440 experimental profile
- Browser metrics for infer FPS, final FPS, current/peak VRAM, TTS time, LLM
  first-token time, total start latency and process memory
- Recoverable CUDA OOM handling with a Chinese 720P recommendation
- OOM count reporting

Automated tests:

- Performance/OOM tests: 2 passed
- Stage 3/4/6 regression tests: 26 passed
- 720P real EdgeTTS stress: 10 / 10 messages passed
- 1080P experiment: 3 / 3 messages passed

Full measurements and decisions are in `docs/PERFORMANCE_REPORT.md`.
