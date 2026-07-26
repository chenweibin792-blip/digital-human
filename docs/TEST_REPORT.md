# Test Report

Date: 2026-07-26

## Environment

- Windows 11 x64, build 26200
- PowerShell 5.1.26100.8875
- Python 3.12.13 in `E:\SZR\.conda\envs\livetalking-local`
- PyTorch 2.9.1+cu128, compiled CUDA 12.8
- NVIDIA GeForce RTX 4060 Laptop GPU, 8187.5 MB VRAM
- NVIDIA driver 537.53
- FFmpeg 8.1.2
- 16 GB system memory
- Upstream commit `a5a77f4c395c8347789a16da1843cd1b08b48eea`
- Branch `codex/local-digital-human`
- Wav2Lip256, EdgeTTS, WebRTC, one session

Browser checks used Playwright 1.54.1 with the installed Microsoft Edge
executable. The Browser plugin was not available. Playwright dependencies,
profiles, screenshots and temporary output were kept under `E:\SZR`.

## Automated regression

Command:

```powershell
E:\SZR\.conda\envs\livetalking-local\python.exe -m unittest tests.test_edge_tts_stage3 tests.test_llm_stage4 tests.test_session_stage6 tests.test_performance_stage7 -v
```

Result: 29 tests passed. The suite covers EdgeTTS validation, safe segmentation,
temporary file naming and cleanup, network errors, LLM stream/non-stream,
history isolation and limits, clear/cancel, missing configuration, 401, 404,
429, timeout, unavailable service, non-JSON, empty output, interrupted streams,
session concurrency, queue flushing, re-entrant RTC close and CUDA OOM recovery.

`python -m compileall` and `git diff --check` also passed.

## Environment and negative checks

| Check | Command or method | Actual result |
| --- | --- | --- |
| Environment | `scripts\check_environment.ps1` | CUDA, GPU, Python and FFmpeg detected |
| Model | `scripts\check_models.ps1` | checkpoint and default Avatar passed |
| Port conflict | environment check while 8010 listened | exit 1 with explicit port failure |
| Missing model | model check with absent test Avatar ID | exit 2; four required items reported |
| Missing FFmpeg | safe override to absent E: path | exit 1 with explicit FFmpeg failure |
| CUDA unavailable | safe simulation flag | exit 1 with explicit CUDA failure |
| Start/stop | `start.ps1`, then controlled process stop | started on 127.0.0.1 without `.env`; clean stop freed port 8010 |

The negative checks use test-only script flags and do not rename or damage the
real model, FFmpeg or CUDA environment. Evidence is in
`E:\SZR\.tmp\stage8-*.txt`.

## Functional browser results

| Scenario | Actual result |
| --- | --- |
| Direct speech | Real EdgeTTS audio drove Wav2Lip over WebRTC |
| AI answer | Local OpenAI-compatible mock answered and drove TTS |
| Multi-turn and clear | isolated history, multiple turns and current-session clear passed |
| Stop during speech | audio became silent, tracks stayed live, later speech succeeded |
| Refresh/reconnect | three distinct sessions connected successfully |
| Repeated connect/disconnect | three sessions released; active count returned to zero |
| Abrupt peer close | session automatically released within the 12-second observation window |
| Rapid double send | one `/human` request; Chinese busy message; peer stayed connected |
| SSE completion loss | SSE was deliberately closed; status polling restored the button for 10/10 messages |
| Voice and controls | voice, rate, volume and pitch update paths passed |
| Desktop/mobile | desktop and portrait mobile layouts rendered without page/console/request errors |

The no-SSE ten-message test completed in 92.0 seconds with infer FPS 48.7934,
final FPS 24.7940, 207.9 MB allocated VRAM and zero OOMs.

## Performance

The dedicated 720P ten-message run completed 10/10 messages:

| Metric | Result |
| --- | ---: |
| Resolution | 720 x 960 |
| Infer FPS | 62.8163 |
| Final FPS | 24.9251 |
| Current / peak allocated VRAM | 207.9 / 1224.1 MB |
| Process memory growth | 52.4 MB |
| Last TTS / start latency | 1.5887 / 1.5894 s |
| OOM | 0 |
| Wall/media clock delta | 0.02 s |

The short 1080P experiment completed 3/3 messages at 1080 x 1440 with infer FPS
53.6826, final FPS 24.9691, zero OOM and 0.03-second clock delta. It remains
experimental. Full details are in `docs/PERFORMANCE_REPORT.md`.

## Long-duration stability

The final repaired 720P run completed successfully:

| Metric | Result |
| --- | ---: |
| Duration | 1800.9 s |
| Messages / samples | 10 / 60 |
| WebRTC states | connected only |
| Infer / final FPS | 57.2646 / 24.9543 |
| Process memory min / max | 2527.1 / 6073.9 MB |
| End-to-start process growth | -3524.5 MB |
| Allocated VRAM min / max / growth | 207.9 / 207.9 / 0 MB |
| CUDA OOM | 0 |
| Wall/media clock delta | 0.02 s |
| Peak system memory | 87.5% |
| Browser/page/request issues | 0 |

The script exited successfully after 1800.9 seconds. Evidence:
`E:\SZR\.tmp\stage8-soak-final.stdout.log`.

During stage 8 an earlier dirty-process soak exposed media worker leakage after
repeated session creation. A later run exposed a missed-SSE UI completion state.
Both were fixed: `RTCManager` now owns and stops each `HumanPlayer`, guards
re-entrant close, bounds peer close time, and the UI reconciles completion from
the backend `request_active` metric. The results above and the final soak use
the repaired lifecycle.

## API recovery and evidence boundary

The service starts and WebRTC direct speech works when the LLM endpoint is
offline. Unavailable API requests return a Chinese error without exposing
headers or credentials. After the local mock returned, a fresh request in a new
session passed (`{"answer":true,"peer":"connected"}`).

Two fixed-window attempts to prove recovery in the exact same browser session
were timing-sensitive and did not complete deterministically. The HTTP client
is reset after connection/timeout errors, but this exact same-session recovery
case remains a known validation boundary. No real provider key was supplied;
all AI integration results are from a local mock and must not be described as a
real-provider acceptance.

## Security

- Frontend and project logs contained zero matches for the test key,
  `LLM_API_KEY` or a Bearer header.
- `.env`, `models\wav2lip.pth`, generated Avatar data and logs are ignored.
- `git ls-files` contains no `.env` or model weight.
- API/admin configuration redacts keys, tokens and secrets.
- User text is never used as a path; EdgeTTS uses random UUID filenames.
- EdgeTTS temporary directory was empty after tests.
- Error tests return Chinese summaries without request headers or credentials.

## Known issues and limits

1. Real OpenAI-compatible providers were not tested; validate the selected
   provider, model, billing and streaming behavior with the user's own key.
2. The exact same-session API-offline-to-online recovery test was not
   deterministic; reconnecting creates a clean session and passed.
3. System memory can reach more than 80% on this 16 GB machine because the
   default Avatar keeps hundreds of full and face frames in memory. Avoid other
   memory-heavy applications.
4. 1080P is experimental and did not receive the 720P long-duration coverage.
5. Browser automation does not replace subjective real-device lip-sync and
   mobile-network acceptance.
6. Wav2Lip and the default Avatar are not approved for commercial use by the
   available license materials.

## Visual evidence

- `E:\SZR\.tmp\stage5-desktop-ai.png`
- `E:\SZR\.tmp\stage5-mobile.png`
- `E:\SZR\.tmp\stage6-interrupted.png`
- `E:\SZR\.tmp\stage7-720-ten-messages.png`
- `E:\SZR\.tmp\stage7-1080-experimental.png`
