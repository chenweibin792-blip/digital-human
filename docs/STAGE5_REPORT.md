# Stage 5 Report: WebRTC Frontend

Date: 2026-07-26

## Result

Stage 5 passed on desktop and mobile viewports using the existing native
HTML/CSS/JavaScript WebRTC implementation. No React, Next.js or external
runtime asset was introduced.

## User-Facing Changes

- Reworked the main page as a focused local digital-human studio.
- Preserved the original audio upload, recording, custom action, admin,
  avatar and TTS management features under the advanced tools section.
- Added clear Chinese states:
  - disconnected
  - connecting
  - connected
  - generating answer
  - synthesizing speech
  - speaking
  - interrupted
  - connection failed
- Added direct-read / AI-answer mode switching.
- Added per-message voice, rate, volume and pitch controls.
- Added conversation history, stop and clear controls.
- Added duplicate-submit protection and busy states.
- Added SSE-driven LLM/TTS state updates.
- Added infer FPS, final FPS, current VRAM and peak VRAM displays.
- Added responsive portrait layout without horizontal page overflow.
- Added refresh auto-reconnect and manual reconnect.
- Default server bind changed to `127.0.0.1`.
- LAN access requires explicit `start.ps1 -Lan` or `--host 0.0.0.0`.

## Browser Environment

- URL: `http://127.0.0.1:8010/index.html`
- Desktop viewport: 1440 x 1000
- Mobile viewport: 390 x 844
- Browser plugin: not available
- Fallback: Playwright 1.54.1 with the existing Microsoft Edge executable

## Functional Browser Result

- Page identity and meaningful content: passed
- Framework error overlay: none
- WebRTC connection: passed
- Video: 576 x 768, ready state 4, live track
- Direct EdgeTTS read: passed
- Mock AI answer displayed and spoken: passed
- WebRTC audio track: live, unmuted
- Maximum audio RMS: 0.212740
- Conversation messages before clear: 3
- Conversation messages after clear: 0
- Infer FPS: 59.2
- Final FPS: 25.0
- Current allocated VRAM: 207.9 MB
- Peak allocated VRAM: 1224.1 MB
- Mobile horizontal overflow: none
- Failed requests: 0
- HTTP errors: 0
- Console errors: 0
- Page errors: 0

## Refresh and Reconnect

Three distinct sessions were created successfully:

1. Initial connection
2. Automatic connection after refresh
3. Manual reconnect

No HTTP error was observed. A stale-session race found during testing was fixed
by explicitly associating each session ID with its PeerConnection and closing
the previous session before creating a replacement.

## Evidence

- `E:\SZR\.tmp\stage5-desktop-ai.png`
- `E:\SZR\.tmp\stage5-mobile.png`
- `E:\SZR\.tmp\stage5-browser-qa.js`
- `E:\SZR\.tmp\stage5-reconnect-qa.js`

## Remaining Boundary

The AI-answer test used the bundled local OpenAI-compatible mock. A real
provider still requires the user to configure `.env` and run one live smoke
test.
