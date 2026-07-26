###############################################################################
#  配置解析 — CLI 参数 + YAML 配置
###############################################################################

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"), override=False)

try:
    import yaml
    _has_yaml = True
except ImportError:
    _has_yaml = False


def str_or_int(value):
    """尝试转换为 int，失败则返回 str"""
    try:
        return int(value)
    except ValueError:
        return value


def _yaml_to_args(yaml_cfg):
    """将 YAML 字典中的 key 转换为 argparse 兼容的 `--key` 形式。

    argparse 的 dest 默认规则：`--model` → `model`，`--push-url` → `push_url`。
    此函数同时支持两种 key 写法：
      - model / batch_size          → 直接透传
      - model-name / batch-size    → 转换为 model_name / batch_size
    """
    result = {}
    for k, v in yaml_cfg.items():
        dest = k.replace('-', '_')
        result[dest] = v
    return result


def parse_args():
    """解析命令行参数，支持 YAML 配置文件覆盖默认值。

    优先级：CLI 参数 > YAML 配置文件 > add_argument(default=...)
    """
    parser = argparse.ArgumentParser(description="LiveTalking Digital Human Server")

    # ─── 配置文件 ──────────────────────────────────────────────────────
    parser.add_argument('--config', '-c', type=str, default='config.yaml',
                        help='YAML 配置文件路径（设为空字符串可跳过）')

    # ─── 音频 ──────────────────────────────────────────────────────────
    parser.add_argument('--fps', type=int, default=25, help="video fps, must be 25")
    parser.add_argument('-l', type=int, default=10)
    parser.add_argument('-m', type=int, default=8)
    parser.add_argument('-r', type=int, default=10)

    # ─── 画面 ──────────────────────────────────────────────────────────
    # parser.add_argument('--W', type=int, default=450, help="GUI width")
    # parser.add_argument('--H', type=int, default=450, help="GUI height")

    # ─── 数字人模型 ────────────────────────────────────────────────────
    parser.add_argument('--model', type=str, default='wav2lip',
                        help="avatar model: musetalk/wav2lip/ultralight")
    parser.add_argument('--avatar_id', type=str, default='wav2lip256_avatar1',
                        help="avatar id in data/avatars")
    parser.add_argument('--batch_size', type=int, default=16, help="infer batch")
    parser.add_argument('--modelres', type=int, default=192)
    parser.add_argument('--modelfile', type=str, default='')
    parser.add_argument('--video_profile', type=str, default='720p',
                        choices=['source', '720p', '1080p'],
                        help='portrait output profile; 1080p is experimental')

    # ─── 自定义动作和多形象 ────────────────────────────────────────────
    parser.add_argument('--customvideo_config', type=str, default='',
                        help="custom action json")

    # ─── TTS ───────────────────────────────────────────────────────────
    parser.add_argument('--TTS_PROVIDER', type=str,
                        default=os.getenv("TTS_PROVIDER", "edge"))
    parser.add_argument('--tts', type=str, default='edgetts',
                        help="tts plugin: edgetts/gpt-sovits/cosyvoice/fishtts/tencent/doubao/indextts2/azuretts/qwentts")
    parser.add_argument('--EDGE_TTS_VOICE', type=str,
                        default=os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural"))
    parser.add_argument('--EDGE_TTS_RATE', type=str,
                        default=os.getenv("EDGE_TTS_RATE", "+0%"))
    parser.add_argument('--EDGE_TTS_VOLUME', type=str,
                        default=os.getenv("EDGE_TTS_VOLUME", "+0%"))
    parser.add_argument('--EDGE_TTS_PITCH', type=str,
                        default=os.getenv("EDGE_TTS_PITCH", "+0Hz"))
    parser.add_argument('--TTS_TIMEOUT_SECONDS', type=float,
                        default=float(os.getenv("TTS_TIMEOUT_SECONDS", "30")))
    parser.add_argument('--REF_FILE', type=str, default="",
                        help="参考文件名或语音模型ID")
    parser.add_argument('--REF_TEXT', type=str, default=None)
    parser.add_argument('--TTS_SERVER', type=str, default='http://127.0.0.1:9880')

    # OpenAI-compatible online LLM. Credentials are read from .env only.
    parser.add_argument('--LLM_PROVIDER', type=str,
                        default=os.getenv("LLM_PROVIDER", "openai_compatible"))
    parser.add_argument('--LLM_BASE_URL', type=str,
                        default=os.getenv("LLM_BASE_URL", ""))
    parser.add_argument('--LLM_API_KEY', type=str,
                        default=os.getenv("LLM_API_KEY", ""))
    parser.add_argument('--LLM_MODEL', type=str,
                        default=os.getenv("LLM_MODEL", ""))
    parser.add_argument('--LLM_TIMEOUT_SECONDS', type=float,
                        default=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")))
    parser.add_argument('--LLM_MAX_RETRIES', type=int,
                        default=int(os.getenv("LLM_MAX_RETRIES", "2")))
    parser.add_argument('--LLM_TEMPERATURE', type=float,
                        default=float(os.getenv("LLM_TEMPERATURE", "0.7")))
    parser.add_argument('--LLM_MAX_HISTORY_TURNS', type=int,
                        default=int(os.getenv("LLM_MAX_HISTORY_TURNS", "10")))
    parser.add_argument('--LLM_STREAM', type=str,
                        default=os.getenv("LLM_STREAM", "true"))
    parser.add_argument('--SYSTEM_PROMPT', type=str,
                        default=os.getenv(
                            "SYSTEM_PROMPT",
                            "你是一名简洁、自然、友好的AI数字人助手。",
                        ))

    # ─── 传输 ─────────────────────────────────────────────────────────
    parser.add_argument('--transport', type=str, default='webrtc',
                        help="output: rtcpush/webrtc/rtmp/virtualcam")
    parser.add_argument('--stun', type=str, default='stun:stun.freeswitch.org:3478',
                        help="stun server url")
    parser.add_argument('--push_url', type=str,
                        default='http://localhost:1985/rtc/v1/whip/?app=live&stream=livestream')
    parser.add_argument('--max_session', type=int, default=1)
    parser.add_argument('--listenport', type=int, default=8010,
                        help="web listen port")
    parser.add_argument('--host', type=str,
                        default=os.getenv("LIVETALKING_HOST", "127.0.0.1"),
                        choices=["127.0.0.1", "0.0.0.0"],
                        help="bind address; use 0.0.0.0 only for explicit LAN mode")

    # ─── 虚拟摄像头 ───────────────────────────────────────────────────
    parser.add_argument('--audio_output_device', type=int, default=None,
                        help="音频输出设备索引（None=系统默认，仅用于 --transport=virtualcam）。使用 python list_audio_devices.py 查看所有设备")

    # ─── 加载 YAML 配置文件 ────────────────────────────────────────────
    if _has_yaml:
        # 先用 parser 的已知参数做一次临时解析，只拿 --config 的值
        tmp_opt, _ = parser.parse_known_args()
        config_path = tmp_opt.config
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                yaml_cfg = yaml.safe_load(f)
            if yaml_cfg and isinstance(yaml_cfg, dict):
                yaml_defaults = _yaml_to_args(yaml_cfg)
                parser.set_defaults(**yaml_defaults)
    else:
        print("[config] PyYAML 未安装，跳过 YAML 配置文件加载。"
              "安装: pip install pyyaml")

    # ─── 正式解析 CLI 参数 ─────────────────────────────────────────────
    opt = parser.parse_args()

    # ─── 后处理 ────────────────────────────────────────────────────────
    opt.customopt = []
    if opt.customvideo_config:
        with open(opt.customvideo_config, 'r') as f:
            opt.customopt = json.load(f)

    return opt
