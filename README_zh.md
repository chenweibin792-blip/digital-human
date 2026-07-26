# LiveTalking 本地实时 AI 数字人

本项目是在官方 LiveTalking 上进行的 Windows 本地适配与小范围增强。默认使用
Wav2Lip256、EdgeTTS、OpenAI 兼容在线 API 和 WebRTC，面向单用户、单数字人，
默认输出 720×960、25 FPS。

> 当前 Wav2Lip 权重和默认 Avatar 的授权材料不足以支持商业使用。本项目仅用于
> 个人学习、研究和技术原型。详见 `LICENSES_AND_LIMITATIONS.md`。

## 新手十步启动

1. **安装环境**：按 `docs/INSTALL_WINDOWS.md` 准备 Git、NVIDIA 驱动和项目自带的
   Conda 环境。当前可复现环境位于 `E:\SZR\.conda\envs\livetalking-local`。
2. **准备模型**：按 `MODEL_SOURCES.md` 从官方地址取得 `models\wav2lip.pth` 和
   `data\avatars\wav2lip256_avatar1`，不要从不明整合包下载。
3. **复制配置**：在项目目录执行
   `Copy-Item .env.example .env`。
4. **填写大模型 API**：只在 `.env` 中填写 `LLM_BASE_URL`、`LLM_API_KEY` 和
   `LLM_MODEL`。不要把密钥写进源码、网页或提交记录。
5. **检查环境**：执行
   `powershell -ExecutionPolicy Bypass -File .\scripts\check_environment.ps1`。
6. **检查模型**：执行
   `powershell -ExecutionPolicy Bypass -File .\scripts\check_models.ps1`。
7. **启动服务**：双击 `start.bat`，或在 PowerShell 中执行 `.\start.ps1`。
8. **打开网页**：访问 <http://127.0.0.1:8010/index.html>，点击“建立连接”。
9. **输入文字**：选择“直接朗读”或“AI 回答”，输入中文后发送；可停止说话、
   清空对话、切换声音并查看性能指标。
10. **处理常见错误**：先运行 `.\scripts\diagnose.ps1`，再查阅
    `docs/TROUBLESHOOTING.md`。

## 局域网与实验模式

默认服务只监听 `127.0.0.1`。需要手机访问时，显式执行 `.\start.ps1 -Lan`，
并按终端显示的局域网地址访问；必要时仅为当前专用网络放行 TCP 8010。

1080P 为实验模式：

```powershell
.\start.ps1 --video_profile 1080p
```

默认 720P 已完成十条消息和30分钟稳定性验收。不要同时运行本地大语言模型。

## 互动动作

连接后可以直接输入“请蹲下”“站起来”“点点头”“摇摇头”或“请鞠躬”，
也可以点击视频下方的快捷动作按钮。纯动作指令不会发送给TTS或大模型。
默认Wav2Lip没有全身骨骼，因此当前为即时2D视觉动作；真实全身动作的素材接入
方式和限制见 `docs/INTERACTIONS.md`。

## 更多文档

- 安装：`docs/INSTALL_WINDOWS.md`
- 配置：`docs/CONFIGURATION.md`
- 在线 API：`docs/API_CONFIGURATION.md`
- 自定义数字人：`docs/CUSTOM_AVATAR.md`
- 互动动作：`docs/INTERACTIONS.md`
- 排错：`docs/TROUBLESHOOTING.md`
- 测试与性能：`docs/TEST_REPORT.md`、`docs/PERFORMANCE_REPORT.md`
