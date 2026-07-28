# LiveTalking 2D 数字人优化报告

日期：2026-07-28  
状态：第一轮正确性与可观测性优化完成；画质与端到端量化待后续固定样本验证。

## 1. 本轮结论

本轮保留了现有 Wav2Lip256、EdgeTTS、在线 LLM、WebRTC、接口和前端。
没有引入 3D、额外模型、超分辨率或新的前端框架。

根据真实代码审计，本轮优先修复媒体时钟和中断队列的正确性问题：

1. WebRTC 音视频节拍从系统墙上时钟改为单调时钟；
2. 队列断粮或中断后不再突发“追赶”积欠帧；
3. 中断清队列会正确唤醒被满队列阻塞的生产者；
4. 增加媒体重基准、最大迟到和音视频队列深度指标；
5. 增加可重复的 CPU 启动基线脚本。

## 2. 关键修改

### `server/webrtc.py`

- 使用 `time.perf_counter()` 驱动音视频节拍，避免系统时间校准造成跳变。
- PTS 继续按固定媒体时间基严格单调递增。
- 当队列断粮导致计划时间落后超过两个 packet duration 时，只重设节拍基准，
  不回退 PTS，也不突发发送积欠帧。
- 记录 `media_clock_rebases`、`media_max_late_ms`、
  `audio_queue_frames` 和 `video_queue_frames`。
- WebRTC track 停止和 flush 改用线程安全队列清理。

### `utils/queues.py`

- 新增统一 `drain_queue()`。
- 通过 `Queue.get_nowait()` 清空队列，使 Python Queue 正确通知
  `not_full` 条件变量，解除阻塞中的生产者。

### `tts/base_tts.py`、`avatars/audio_features/base_asr.py`

- TTS 和 ASR 中断清理统一使用 `drain_queue()`。

### `avatars/base_avatar.py`

- 推理结果队列中断清理改为线程安全实现。
- 初始化新增媒体时钟和队列观测指标，自动出现在现有运行状态接口。

### `scripts/measure_cpu_baseline.ps1`

- 使用独立 8011 端口启动 CPU 服务。
- 测量模型加载/warm-up 到 HTTP 200 的时间与 Working Set。
- 测试完成后只终止自己启动的确切进程。

### `tests/test_media_clock_optimization.py`

- 验证队列清理会唤醒阻塞生产者。
- 验证长时间断粮后 PTS 仍严格单调，并触发节拍重基准。

## 3. 前后差异

| 项目 | 修改前 | 修改后 | 验证 |
| --- | --- | --- | --- |
| 节拍时钟 | `time.time()`，受系统时间调整影响 | `time.perf_counter()` 单调时钟 | 新增单元测试 |
| 断粮恢复 | 计划落后时连续无等待追帧 | 超过 2 个包周期后重设节拍基准 | 模拟 920 ms 断粮通过 |
| PTS | 固定步进 | 固定步进，重基准后仍为 0/3600/7200 | 单元测试通过 |
| 清队列 | 直接 `queue.queue.clear()` | 公共 API drain 并通知生产者 | 阻塞生产者测试通过 |
| 队列诊断 | 只有视频 buffer size | 音频、视频队列帧数均进入 runtime metrics | 代码路径验证 |
| CPU 启动基线 | 无当前机器记录 | 两次均成功，24.503/24.476 s；Working Set 1,454.8–2,128.2 MB | 独立进程实测两次 |

本轮属于正确性优化，不能把模拟断粮测试写成真实口型或端到端延迟提升。

## 4. 验证命令

```powershell
# 新增时钟与队列测试
E:\Anaconda\envs\DIGITAL-HUMAN\python.exe -m unittest `
  tests.test_media_clock_optimization -v

# 完整阶段回归
E:\Anaconda\envs\DIGITAL-HUMAN\python.exe -m unittest `
  tests.test_edge_tts_stage3 `
  tests.test_llm_stage4 `
  tests.test_session_stage6 `
  tests.test_performance_stage7 `
  tests.test_media_clock_optimization -v

# CPU 启动基线
powershell -ExecutionPolicy Bypass -File .\scripts\measure_cpu_baseline.ps1
```

## 5. 运行与观察

双击：

```text
START-DIGITAL-HUMAN.bat
```

运行后可通过现有 runtime status 接口观察：

- `media_clock_rebases`
- `media_max_late_ms`
- `audio_queue_frames`
- `video_queue_frames`
- `inferfps`
- `finalfps`
- `process_memory_mb`

正常持续播放时，重基准计数应保持低位；中断、浏览器暂停或队列断粮时允许增加。
若队列帧数持续只增不减，应视为背压或消费异常。

## 6. 风险与回退

- 重基准阈值当前是各轨道两个 packet duration：视频 80 ms、音频 40 ms。
  这是保守正确性阈值，仍需结合真实浏览器统计调优。
- 音频和视频仍各有自己的 aiortc track PTS；本轮没有引入共享播放时钟协议。
- 未完成固定视频的画质、融合边界和音画偏差测量，因此没有调整 bbox、mask、
  锐化或编码参数。
- 回退本轮媒体修改时，只需恢复 `server/webrtc.py` 的节拍逻辑及四处
  `drain_queue()` 调用；不涉及模型和资产格式。

## 7. 下一轮优先级

1. 浏览器采集 `getStats()`，把 RTT、jitter、framesDropped 和 decode time
   关联到 session/runtime status。
2. 给 request/session/utterance 增加统一 trace，并采集首 TTS、首音频和首视频帧。
3. 用固定脉冲音频和固定头像生成可复核的音画偏差测量。
4. 完成 CPU 模式 10 轮对话及 30 分钟长稳。
5. 有了固定视频证据后，再评估 bbox 平滑、融合 mask 与颜色匹配；无量化证据前
   不启用超分辨率或锐化。
