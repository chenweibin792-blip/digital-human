# Agent working agreement

## Project structure

- `app.py`, `server/`: aiohttp service, routes, sessions and WebRTC.
- `avatars/`: avatar model implementations and audio features.
- `tts/`: registered TTS implementations; EdgeTTS is the default.
- `web/`: dependency-free browser UI and WebRTC client.
- `models/`, `data/avatars/`: local weights and prepared avatar assets.
- `scripts/`: Windows checks and diagnostics.
- `tests/`: stage regression tests.
- `docs/`: installation, configuration, test and limitation records.

## Start and test

Start locally with `.\start.ps1`; use `.\start.ps1 -Lan` only when LAN exposure
is intentional. The direct app command is:

```powershell
E:\SZR\.conda\envs\livetalking-local\python.exe app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1 --tts edgetts
```

Run regression tests with:

```powershell
E:\SZR\.conda\envs\livetalking-local\python.exe -m unittest tests.test_edge_tts_stage3 tests.test_llm_stage4 tests.test_session_stage6 tests.test_performance_stage7 -v
```

## Change rules

- Read the existing LiveTalking implementation before modifying it.
- Prefer the existing registry and extension points; do not duplicate TTS,
  avatar, LLM or transport systems.
- Keep configuration in `config.yaml`, CLI arguments or `.env`.
- Never commit `.env`, API keys, model weights, generated avatar caches, audio,
  video, logs or temporary files.
- Make the smallest maintainable change and test after every modification.
- Preserve existing features and keep default concurrency at one.
- New local dependencies, caches and temporary files for this checkout belong
  under `E:\SZR`, not C:.
- Wav2Lip upstream pretrained results are restricted to personal, research and
  non-commercial use. Do not represent this checkout as commercially licensed.
- Keep the avatar registry replaceable so a properly licensed MuseTalk model can
  be selected later without rewriting the service architecture.

