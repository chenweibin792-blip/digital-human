# Windows 安装

## 前提

- Windows 11 x64
- NVIDIA RTX 4060 Laptop 或兼容显卡及可用驱动
- Git、PowerShell 5.1+、约 10 GB 可用空间
- Conda 环境和缓存放在 E 盘

本机验收使用 Python 3.12.13、PyTorch 2.9.1+cu128 和 PyTorch 自带 CUDA
运行时；不要求额外安装系统级 CUDA Toolkit。

## 目录

建议结构：

```text
E:\SZR\
  LiveTalking\
  .conda\envs\livetalking-local\
  .cache\
  .tmp\
```

安装依赖前请阅读 `docs/DEPENDENCY_PLAN_WINDOWS.md`。可复现版本记录在
`requirements-windows-lock.txt`。所有命令都应在项目目录运行，并把
`TEMP`、`TMP`、`PIP_CACHE_DIR`、`HF_HOME` 指向 `E:\SZR` 下的目录。

## 模型

只使用 `MODEL_SOURCES.md` 中记录的官方来源。最终应存在：

```text
models\wav2lip.pth
data\avatars\wav2lip256_avatar1\coords.pkl
data\avatars\wav2lip256_avatar1\full_imgs\
data\avatars\wav2lip256_avatar1\face_imgs\
```

执行：

```powershell
Copy-Item .env.example .env
powershell -ExecutionPolicy Bypass -File .\scripts\check_environment.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\check_models.ps1
.\start.ps1
```

打开 <http://127.0.0.1:8010/index.html>。停止服务时在启动窗口按 Ctrl+C。

