# 常见问题

先运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\diagnose.ps1
```

## 端口 8010 被占用

关闭旧的 LiveTalking 进程，或确认用途后使用其他端口：
`.\start.ps1 -Port 8011`。浏览器地址也要改为对应端口。

## CUDA 不可用或显存不足

更新 NVIDIA 驱动并确认诊断输出中的 `torch.cuda.is_available()` 为 True。
无需先安装系统级 CUDA Toolkit。本配置发生 OOM 时会中止当前任务并建议回到
720P；同时关闭其他占显存或大量内存的程序。

## 模型或 Avatar 缺失

按 `MODEL_SOURCES.md` 从官方来源重新准备文件，再运行
`scripts\check_models.ps1`。不要通过跳过检查来启动。

## FFmpeg 缺失

本机使用 Conda 环境中的 `Library\bin\ffmpeg.exe`。修复环境或依赖后重新运行
环境检查，不要只把未知版本复制到项目。

## AI 回答失败

检查 `.env` 的 Base URL、模型名和密钥；401 表示认证失败，429 表示限流，
超时或服务不可用会返回中文错误但不会关闭 WebRTC。真实供应商未在交付时认证。

## EdgeTTS 失败

确认网络可访问语音服务，换回 `zh-CN-XiaoxiaoNeural`，并检查语速、音量和
音调格式。临时文件位于 E 盘并会清理。

## 手机无法访问

默认仅本机可用。使用 `.\start.ps1 -Lan`，让手机与电脑处于同一可信网络，
按终端显示地址访问；必要时仅对专用网络放行 TCP 8010。公共网络不要开放。

## 页面卡住或重复发送

点击“停止说话”后重试；如连接断开，点击“重新连接”或刷新页面。页面会阻止
同一会话并发提交，服务默认只允许一个会话。

