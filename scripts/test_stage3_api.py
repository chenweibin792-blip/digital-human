"""Stage 3 HTTP acceptance checks against a running local server."""

from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.request
import wave


BASE_URL = "http://127.0.0.1:8010"


def request(path, method="GET", payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read()


def json_body(body):
    return json.loads(body.decode("utf-8"))


def assert_wav(body):
    with wave.open(io.BytesIO(body), "rb") as wav:
        assert wav.getframerate() == 16_000
        assert wav.getnchannels() == 1
        assert wav.getnframes() > 0
        return round(wav.getnframes() / wav.getframerate(), 3)


def main():
    status, _, body = request("/api/tts/config")
    config = json_body(body)
    assert status == 200 and config["voice"] == "zh-CN-XiaoxiaoNeural"
    print("PASS config", config)

    status, _, body = request("/api/tts/voices?locale=zh-CN")
    voices = json_body(body)
    names = [item["ShortName"] for item in voices["voices"]]
    assert status == 200 and "zh-CN-XiaoxiaoNeural" in names
    print("PASS voices", voices["count"])

    changed = {
        "voice": "zh-CN-YunxiNeural",
        "rate": "+10%",
        "volume": "-5%",
        "pitch": "+15Hz",
        "timeout_seconds": 30,
    }
    status, _, body = request("/api/tts/config", "POST", changed)
    assert status == 200 and json_body(body)["rate"] == "+10%"
    print("PASS runtime config update")

    synthesis_cases = {
        "short": "你好，阶段三接口测试。",
        "punctuation_digits_mixed": "订单20260726：总计123.45元！LiveTalking OK？",
        "long_segmented": "这是一段需要安全分段的较长中文文本。" * 35,
    }
    for name, text in synthesis_cases.items():
        status, headers, body = request(
            "/v1/audio/speech",
            "POST",
            {
                "input": text,
                "voice": "zh-CN-XiaoxiaoNeural",
                "response_format": "wav",
                "rate": "+0%",
                "volume": "+0%",
                "pitch": "+0Hz",
            },
        )
        assert status == 200 and headers.get_content_type() == "audio/wav"
        print("PASS", name, "seconds", assert_wav(body), "bytes", len(body))

    invalid_cases = [
        ({"input": "", "voice": "zh-CN-XiaoxiaoNeural"}, "文本不能为空"),
        ({"input": "长" * 20_001, "voice": "zh-CN-XiaoxiaoNeural"}, "文本过长"),
        (
            {
                "input": "格式测试",
                "voice": "zh-CN-XiaoxiaoNeural",
                "response_format": "mp3",
            },
            "仅支持 WAV",
        ),
    ]
    for payload, expected in invalid_cases:
        status, _, body = request("/v1/audio/speech", "POST", payload)
        message = json_body(body)["message"]
        assert status == 400 and expected in message
        print("PASS safe error", expected)

    defaults = {
        "voice": "zh-CN-XiaoxiaoNeural",
        "rate": "+0%",
        "volume": "+0%",
        "pitch": "+0Hz",
        "timeout_seconds": 30,
    }
    status, _, _ = request("/api/tts/config", "POST", defaults)
    assert status == 200
    print("PASS config restored")
    return 0


if __name__ == "__main__":
    sys.exit(main())
