# LiveTalking 2D 数字人当前基线

日期：2026-07-28  
项目：`E:\digital-human`  
范围：现有 Wav2Lip256 + EdgeTTS + WebRTC 2D 链路，不包含 3D。

## 1. 当前环境

| 项目 | 当前值 |
| --- | --- |
| 操作系统 | Windows 11 家庭中文版 10.0.26200 |
| CPU | Intel Core i5-1135G7，4 核 8 线程 |
| 内存 | 15.7 GiB |
| GPU / CUDA | 无可用 GPU；`torch.cuda.is_available() == False` |
| Python | 3.13.14，`DIGITAL-HUMAN` Conda 环境 |
| PyTorch | 2.13.0+cpu |
| OpenCV | 5.0.0 |
| aiortc | 1.15.0 |
| EdgeTTS | 7.2.8 |
| FFmpeg | 7.1，位于 Conda 环境 `Library\bin` |

当前机器与 `docs/PERFORMANCE_REPORT.md` 中 2026-07-26 的 RTX 4060
测试机不同，因此旧 GPU 数据只能作为历史记录，不能作为当前 CPU 优化的前后对照。

## 2. 实际运行配置

| 项目 | 当前值 |
| --- | --- |
| 入口 | `app.py` |
| 启动器 | `START-DIGITAL-HUMAN.bat` |
| 传输 | WebRTC |
| 数字人模型 | LiveTalking Wav2Lip256 |
| checkpoint | `models\wav2lip.pth`，214,670,409 字节 |
| checkpoint SHA-256 | `b22d7ac86295df667644b17254dc71250c2600b89e20403e90e58812450bc173` |
| 默认头像 | `wav2lip256_avatar1`，550 个完整帧及 550 个脸部帧 |
| 输出 | 720 x 960，25 FPS |
| 音频 | 单声道 16 kHz；每包 320 samples / 20 ms |
| 视频时间基 | 90 kHz；每帧 3,600 ticks / 40 ms |
| batch | 16 |
| 推理精度 | CPU FP32 |
| 默认并发 | 1 |

## 3. 真实调用链

```text
浏览器文本
  -> server/routes.py
  -> llm.py（在线 OpenAI-compatible 流式接口，可取消）
  -> tts/edge.py（分句、EdgeTTS、统一为 16 kHz）
  -> avatars/audio_features（mel 特征与音频帧）
  -> avatars/wav2lip_avatar.py（Wav2Lip256 CPU 推理）
  -> avatars/base_avatar.py（帧合成、音视频成对输出）
  -> streamout/webrtc.py
  -> server/webrtc.py（AudioFrame / VideoFrame、PTS、节拍）
  -> aiortc RTCPeerConnection
  -> 浏览器播放
```

会话由 `server/session_manager.py` 管理，连接由 `server/rtc_manager.py`
管理。停止操作会取消 LLM、清理 TTS/ASR/推理/WebRTC 缓冲，并保留共享模型。

## 4. 当前可复现测量

命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\measure_cpu_baseline.ps1
```

结果：

| 指标 | 当前值 | 口径 |
| --- | ---: | --- |
| 启动到 HTTP 200 | 24.503 s、24.476 s | 两次独立新进程；加载模型和头像、warm-up，轮询 `/index.html` |
| HTTP 可用时进程内存 | 1,454.8–2,128.2 MB | 两次 Windows Working Set；仅作为短时范围 |
| 模型与页面启动 | 通过 | CPU 模型加载并完成 warm-up |
| Python 依赖一致性 | 通过 | `python -m pip check` |

两次启动均成功，平均约 24.49 秒。样本仍不足以计算 P50/P95；Working Set
受 Windows 页面驻留影响明显，也不能代替长稳中的私有内存/峰值统计。

## 5. 已有能力

- EdgeTTS 的超时、分段、临时文件清理和错误恢复已有自动化测试。
- LLM 流式输出、会话隔离、取消、错误映射与历史上限已实现。
- WebRTC 会话关闭和重复关闭已有生命周期保护。
- 模型在进程启动时加载并 warm-up，不会每句话重复加载。
- 推理使用 `torch.inference_mode()`，CPU 环境不会误启用 FP16/CUDA。
- 运行状态接口已暴露 FPS、TTS/LLM 时间、内存和请求状态。

## 6. 基线缺口

以下内容尚无当前 CPU 机器上的可复现实测值，不能声称已优化：

- 浏览器首音频、首视频帧和端到端延迟 P50/P95；
- 音画偏差 P50/P95/最大值；
- 固定素材的口型与融合边界前后视频；
- 10 轮真实连续对话和 30 分钟 CPU 长稳；
- 浏览器 `getStats()` 的 RTT、jitter、packet loss、framesDropped；
- 弱网、断网恢复和真实在线 LLM（需要有效 API 配置）。

后续测量必须固定浏览器、网络、测试文本、模型、头像和质量配置。
