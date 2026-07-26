# Performance Report

Date: 2026-07-26

## Test Hardware

- Windows 11 x64
- NVIDIA GeForce RTX 4060 Laptop GPU
- GPU memory: 8187.5 MB
- System memory: 16 GB
- Python: 3.12.13
- PyTorch: 2.9.1+cu128
- Model: Wav2Lip256
- Batch size: 16
- Frame rate: 25 FPS
- Concurrency: 1

## 720P Portrait Profile

Profile output: 720 x 960 at 25 FPS.

Test: ten sequential real EdgeTTS messages over one WebRTC session.

| Metric | Result |
| --- | ---: |
| Completed messages | 10 / 10 |
| Infer FPS | 62.8163 |
| Final FPS | 24.9251 |
| Current allocated VRAM | 207.9 MB |
| Peak allocated VRAM | 1224.1 MB |
| VRAM growth | 0 MB |
| Process memory growth | 52.4 MB |
| Last TTS time | 1.5887 s |
| Last start-to-audio-queue time | 1.5894 s |
| CUDA OOM count | 0 |
| Test wall time | 79.27 s |
| Browser media time | 79.30 s |
| Absolute clock delta | 0.02 s |

The default profile passed the target. The measured final FPS rounds to 25 and
no sustained GPU-memory increase or media-clock drift was observed.

## 1080P Experimental Portrait Profile

Profile output: 1080 x 1440 at 25 FPS.

Test: three sequential real EdgeTTS messages in a separate process.

| Metric | Result |
| --- | ---: |
| Completed messages | 3 / 3 |
| Infer FPS | 53.6826 |
| Final FPS | 24.9691 |
| Peak allocated VRAM | 1224.1 MB |
| VRAM growth | 0 MB |
| Process memory growth | 87.8 MB |
| CUDA OOM count | 0 |
| Absolute clock delta | 0.03 s |

1080P passed this short experiment but remains experimental because it was not
subjected to the same ten-message and long-duration acceptance as 720P. It also
increases browser encoding, network and system-memory pressure.

## Optimization Decisions

- The Wav2Lip model is loaded once at server startup and shared by sessions.
- Wav2Lip inference already runs with gradients disabled.
- The server defaults to one session.
- 720P is the default output profile.
- 1080P must be selected explicitly with `--video_profile 1080p`.
- FP16 was not enabled. FP32 already exceeds the FPS target with low allocated
  VRAM, while changing model precision could alter lip output and requires
  separate visual quality validation.
- CUDA OOM is caught around inference, the current task is flushed, cached CUDA
  blocks are released, the browser receives a Chinese message and the inference
  thread remains alive for a later retry.

## Memory Note

The process used approximately 6.0 GB of system memory because the default
avatar keeps 550 full frames and 550 face crops resident in memory. System
memory reached 83.1% during the 720P test. The memory was stable across the ten
messages, but running other memory-heavy applications at the same time is not
recommended on a 16 GB machine.

## Final 30-Minute Lifecycle Regression

After explicit `HumanPlayer` lifecycle cleanup and status-poll reconciliation
were added, the final 720P soak ran for 1800.9 seconds with ten messages and 60
samples. WebRTC remained connected, infer FPS was 57.2646, final FPS was
24.9543, allocated VRAM growth was 0 MB, OOM count was zero and the wall/media
clock delta was 0.02 seconds. Process memory ranged from 2527.1 to 6073.9 MB
and ended 3524.5 MB below its first sample.

## Evidence

- `E:\SZR\.tmp\stage7-720-ten-messages.png`
- `E:\SZR\.tmp\stage7-1080-experimental.png`
- `E:\SZR\.tmp\stage7-720.stderr.log`
- `E:\SZR\.tmp\stage7-1080.stderr.log`
