# Stage 1 report: source and Windows environment

Date: 2026-07-26

## Baseline

- Repository: `https://github.com/lipku/LiveTalking.git`
- Commit: `a5a77f4c395c8347789a16da1843cd1b08b48eea`
- Branch: `codex/local-digital-human`
- Repository path: `E:\SZR\LiveTalking`
- Environment path: `E:\SZR\.conda\envs\livetalking-local`

## Installed runtime

- Miniforge: `26.3.2-3`
- Conda: `26.3.2`
- Python: `3.12.13`
- FFmpeg: `8.1.2`
- PyTorch: `2.9.1+cu128`
- torchvision: `0.24.1+cu128`
- torchaudio: `2.9.1+cu128`

The downloaded PyTorch wheel was checked against the SHA-256 published in the
official PyTorch package index:

`3a01f0b64c10a82d444d9fd06b3e8c567b1158b76b2764b8f51bfd8f535064b0`

## Verification results

- PowerShell syntax checks for all four scripts: PASS
- Python source compile check (`config.py`, `app.py`, `llm.py`): PASS
- Import smoke test for 20 direct project dependencies: PASS
- `torch.cuda.is_available()`: `true`
- GPU: `NVIDIA GeForce RTX 4060 Laptop GPU`
- CUDA tensor operation: PASS
- FFmpeg executable and runtime: PASS
- Port 8010 availability: PASS
- `start.ps1` missing-model safety stop: PASS
- `start.bat` exit-code propagation and safety stop: PASS

`check_models.ps1` and `diagnose.ps1` return exit code 2 at the end of stage 1.
This is expected: the Wav2Lip checkpoint and prepared avatar belong to stage 2.

## E-drive placement

All controllable tools, environments, package caches, downloads, temporary
files, source files and generated project files are under `E:\SZR`. Windows
system components such as PowerShell and the installed NVIDIA driver remain
at their operating-system paths and were only executed, not modified.
