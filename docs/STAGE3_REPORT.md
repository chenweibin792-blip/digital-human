# Stage 3 Report: EdgeTTS Adaptation

Date: 2026-07-26

## Result

Stage 3 passed. The existing `tts/edge.py` adapter was enhanced and reused;
no parallel or duplicate EdgeTTS adapter was introduced.

## Implemented

- Default natural Chinese voice: `zh-CN-XiaoxiaoNeural`.
- Configuration through `.env`, YAML, and CLI:
  - `TTS_PROVIDER=edge`
  - `EDGE_TTS_VOICE=zh-CN-XiaoxiaoNeural`
  - `EDGE_TTS_RATE=+0%`
  - `EDGE_TTS_VOLUME=+0%`
  - `EDGE_TTS_PITCH=+0Hz`
  - `TTS_TIMEOUT_SECONDS=30`
- Runtime-safe configuration API:
  - `GET /api/tts/config`
  - `POST /api/tts/config`
- Voice list APIs:
  - `GET /api/tts/voices`
  - `GET /v1/audio/voices`
- WAV preview API:
  - `POST /v1/audio/speech`
- Per-message voice/rate/volume/pitch settings through `POST /human`.
- Safe long-text splitting at sentence punctuation with a hard maximum of
  280 characters per network request.
- Input limit of 20,000 characters and explicit empty-input rejection.
- Dedicated temporary directory: `E:\SZR\.tmp\edge-tts`.
- Random UUID filenames that never derive from user input.
- Immediate temporary-file removal after audio decoding and conservative
  expired-cache cleanup limited to owned `edge-*.mp3` files.
- Chinese timeout/network/synthesis errors.
- Provider and worker-level exception protection so a failed synthesis does
  not terminate the service worker.
- Chinese and English EdgeTTS management pages using only local frontend
  dependencies.

## Test Evidence

### Automated unit tests

Command:

```powershell
E:\SZR\.conda\envs\livetalking-local\python.exe -m unittest tests.test_edge_tts_stage3 -v
```

Result: 8 tests passed.

Covered:

- Short Chinese
- Long Chinese
- Chinese punctuation
- Chinese digits
- Chinese-English mix
- Empty text
- Overlong input and safe segmentation
- Network unavailable
- Random temporary filenames
- Expired-cache cleanup boundary
- Voice/rate/volume/pitch validation
- Synthesis failure followed by a successful request

### Real EdgeTTS network test

- Available voices: 322
- `zh-CN` voices: 6
- `zh-CN-XiaoxiaoNeural`: present
- Real mixed-language output: 6.216 seconds, 16 kHz PCM
- Voice, rate, volume, and pitch were changed in the real request

### HTTP API test

Command:

```powershell
E:\SZR\.conda\envs\livetalking-local\python.exe scripts\test_stage3_api.py
```

Result: passed.

- Configuration read/update/restore: passed
- Chinese voice list: passed
- Short synthesis: 3.096 seconds
- Punctuation/digits/mixed synthesis: 7.272 seconds
- Long segmented synthesis: 134.184 seconds
- Empty text: HTTP 400 with Chinese error
- Overlong text: HTTP 400 with Chinese error
- Unsupported audio format: HTTP 400 with Chinese error

### Browser UI test

Playwright 1.54.1 used the existing Microsoft Edge executable because the
Browser plugin was not available in this task.

- Desktop and mobile layouts: passed
- Chinese voice manager: 322 options
- English voice manager: 322 options
- Generated preview: playable 5.472-second WAV blob
- Horizontal mobile overflow: none
- Blocking overlays: none
- Failed requests: 0
- HTTP responses >= 400: 0
- Console errors: 0
- Page errors: 0

Screenshots:

- `E:\SZR\.tmp\stage3-tts-desktop.png`
- `E:\SZR\.tmp\stage3-tts-mobile.png`

### EdgeTTS -> Wav2Lip -> WebRTC test

- `/human` received `zh-CN-XiaoxiaoNeural`, `+7%`, `-2%`, and `+10Hz`.
- Real EdgeTTS synthesis time: 1.6210 seconds.
- WebRTC audio track: live and unmuted.
- Maximum measured audio RMS: 0.149317.
- WebRTC video: 576 x 768, ready state 4, live track.
- Wav2Lip inference: 60.1788 FPS.
- Stable final output: approximately 25 FPS.
- Failed requests: 0.
- Browser console/page errors: 0.
- CUDA out-of-memory errors: 0.

Screenshot:

- `E:\SZR\.tmp\stage3-webrtc-edge.png`

## Acceptance Boundary

The automated browser test verifies a playable audio stream and measures
non-silent WebRTC audio. It does not replace subjective listening for voice
naturalness or human inspection of lip-sync quality. EdgeTTS remains dependent
on Microsoft network availability; failures are now contained and returned in
Chinese without stopping LiveTalking.
