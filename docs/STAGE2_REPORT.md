# Stage 2 report: Wav2Lip256 and default avatar

Date: 2026-07-26

## Delivered assets

- Wav2Lip256 checkpoint: `models/wav2lip.pth`
- Default avatar: `data/avatars/wav2lip256_avatar1`
- Source and licensing record: `MODEL_SOURCES.md`
- Default avatar contents:
  - `550` full frames (`768 x 576`)
  - `550` face frames (`256 x 256`)
  - `550` coordinate records

The official Google Drive archive was enumerated before download and contained
exactly the two files named by the current LiveTalking README. The avatar
archive was checked for absolute paths and parent-directory traversal before
safe extraction.

## Reliability changes

- `web/index.html` and `web/index-en.html` now load Bootstrap 5.3.0 and
  Bootstrap Icons 1.10.0 from `web/vendor`, so the main UI no longer depends on
  jsDelivr at runtime.
- A local SVG favicon prevents missing-icon requests.
- EdgeTTS now retries once after a one-second delay when its WebSocket
  connection fails transiently. A deterministic test simulated a first-attempt
  connection reset and verified success on attempt two.
- `.gitignore` excludes model data, prepared avatars, audio/video cache
  formats, environment secrets, logs and temporary files.

## Model and CUDA validation

- Checkpoint state dictionary loaded successfully on `cuda:0`.
- Official warm-up parameters: batch `16`, resolution `256`.
- Model load: `1.938 s`.
- Avatar load: `0.558 s`.
- Warm-up: `2.028 s`.
- CUDA allocated after warm-up: `207.87 MiB`.
- CUDA reserved after warm-up: `2,156 MiB`.
- CUDA OOM: none.

## Browser and WebRTC validation

Target flow:

`/index.html` -> start WebRTC -> default avatar video -> send Chinese text ->
EdgeTTS audio and Wav2Lip mouth inference.

Browser plugin availability: not installed. Playwright 1.54.1 was installed
under `E:\SZR\.tools\browser-qa` and used the existing Microsoft Edge browser.

Final run:

- URL: `http://127.0.0.1:8010/index.html`
- Page title: `LiveTalking - 数字人实时驱动`
- Viewport: `1440 x 1000`
- WebRTC state: connected
- Session ID assigned: yes
- Remote video: live, `576 x 768`, `readyState=4`
- Remote audio: live and unmuted
- Video timeline advanced before and after text submission: yes
- `POST /human`: HTTP `200`
- Captured audio maximum RMS: `0.150007`
- EdgeTTS generation time: `0.9758 s`
- Reported inference FPS: `56.7808`
- Reported final FPS while speaking: `25.0710`
- Failed browser requests: `0`
- HTTP 4xx/5xx responses: `0`
- Browser console errors/warnings: `0`
- Page script errors: `0`
- CUDA OOM: none
- Session and worker-thread shutdown after browser close: clean

Screenshots:

- `E:\SZR\.tmp\stage2-page-loaded.png`
- `E:\SZR\.tmp\stage2-webrtc-connected.png`
- `E:\SZR\.tmp\stage2-text-sent.png`

## Acceptance boundary

Automated evidence confirms that synchronized audio and generated video were
carried in one live WebRTC session, the video advanced during speech, and the
Wav2Lip inference/final FPS remained stable. Subjective lip-sync quality and
speaker likeness should still be watched and heard by a person on the intended
display/audio hardware before production acceptance.

The downloaded default model and avatar do not include documentation granting
commercial model, training-data or likeness rights. Treat them as
non-commercial evaluation assets unless separate written rights are obtained.
