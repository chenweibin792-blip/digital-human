# 阶段 1：Windows 依赖安装计划

## 固定基线

- 上游仓库：`https://github.com/lipku/LiveTalking.git`
- 上游提交：`a5a77f4c395c8347789a16da1843cd1b08b48eea`
- 开发分支：`codex/local-digital-human`
- Python：3.12
- PyTorch：2.9.1
- torchvision：0.24.1
- torchaudio：2.9.1
- PyTorch CUDA 运行时：cu128
- 默认传输：WebRTC
- 默认模型：Wav2Lip256

以上 Python、PyTorch 和 CUDA 运行时版本来自该固定提交的 `README.md`。

## 项目内目录

所有可控制的依赖、缓存和临时文件均放在 `E:\SZR`：

```text
E:\SZR\
├─ LiveTalking\                 # 源码与项目文档
├─ .tools\miniforge3\           # 独立 Conda 发行版
├─ .conda\envs\livetalking-local\ # 独立 Python 环境
├─ .conda\pkgs\                 # Conda 包缓存
├─ .cache\pip\                  # pip 缓存
├─ .tmp\                        # 安装和运行临时目录
└─ downloads\                   # 安装器下载目录
```

NVIDIA 显卡驱动和 Windows 防火墙属于操作系统组件，无法封装在项目目录中。本阶段不自动修改这两项。

## 安装顺序

1. 下载并静默安装 Miniforge 到 `.tools\miniforge3`。
2. 使用显式路径创建 `.conda\envs\livetalking-local`，不创建全局命名环境。
3. 在该环境中安装 Python 3.12 和 FFmpeg。
4. 使用 PyTorch 官方 cu128 wheel 安装固定版本的 PyTorch 三件套。
5. 安装 `requirements.txt`。
6. 验证 Python、FFmpeg、PyTorch 导入、CUDA 可用性、GPU 名称与显存。
7. 清理无用安装缓存前先确认环境可正常导入。

不预装系统级 CUDA Toolkit。PyTorch wheel 自带 CUDA 运行时；只有后续出现必须本地编译的依赖时才重新评估。

## 风险与回退

- 当前 NVIDIA 驱动为 537.53，低于 CUDA 12.8 对应的新驱动系列。若
  `torch.cuda.is_available()` 为 `False` 或 CUDA 初始化失败，本阶段停止，
  保留完整错误并建议升级驱动。
- E 盘当前空闲约 47 GB。安装期间同时保留环境和包缓存会消耗较多空间；
  验证通过后可安全清理下载器和安装缓存。
- 上游只明确验证 Ubuntu。Windows 下 `aiortc`、PyAV、FFmpeg 或某些科学计算
  包若缺少兼容 wheel，本阶段最多尝试两种有证据的安装方式，然后停止并报告。
