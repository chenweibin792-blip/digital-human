# 配置说明

配置优先级为命令行、`config.yaml`、代码默认值；EdgeTTS 和 LLM 的敏感或
机器相关值建议放在本地 `.env`。启动脚本会读取 `.env`，但不打印值。

## 默认运行

- 模型：`wav2lip`
- Avatar：`wav2lip256_avatar1`
- TTS：`edgetts`
- WebRTC：`webrtc`
- 监听：`127.0.0.1:8010`
- 并发：1
- 视频：720×960、25 FPS

EdgeTTS 变量：

```dotenv
EDGE_TTS_VOICE=zh-CN-XiaoxiaoNeural
EDGE_TTS_RATE=+0%
EDGE_TTS_VOLUME=+0%
EDGE_TTS_PITCH=+0Hz
TTS_TIMEOUT_SECONDS=30
```

页面可在运行时修改声音、语速、音量和音调。数值必须使用 EdgeTTS 接受的
格式，例如 `+10%`、`-5%`、`+2Hz`。

选择实验 1080P：

```powershell
.\start.ps1 --video_profile 1080p
```

显式开启局域网：

```powershell
.\start.ps1 -Lan
```

不要把 `host` 默认改成 `0.0.0.0`，也不要提高并发，除非重新做显存、内存和
稳定性测试。

