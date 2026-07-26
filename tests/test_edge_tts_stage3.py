import os
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import soundfile as sf

from tts.edge import (
    EdgeTTS,
    EdgeTTSError,
    cleanup_expired_cache,
    split_text_safely,
    synthesize_edge_pcm,
    validate_edge_settings,
)


TEST_CACHE = Path(r"E:\SZR\.tmp\stage3-edge-unit")


async def fake_save_segment(segment, target, settings):
    duration = max(0.08, min(0.25, len(segment) / 100))
    samples = np.zeros(int(24_000 * duration), dtype=np.float32)
    sf.write(target, samples, 24_000, format="WAV")


class EdgeTTSStage3Tests(unittest.TestCase):
    def setUp(self):
        TEST_CACHE.mkdir(parents=True, exist_ok=True)
        for item in TEST_CACHE.glob("*"):
            item.unlink()

    def tearDown(self):
        for item in TEST_CACHE.glob("*"):
            item.unlink()
        TEST_CACHE.rmdir()

    def test_required_text_cases_synthesize(self):
        cases = {
            "short_chinese": "你好。",
            "long_chinese": "这是较长的中文语音合成测试。" * 30,
            "punctuation": "你好！今天怎么样？很好；谢谢。",
            "digits": "订单号是20260726，价格为123.45元。",
            "mixed": "LiveTalking 版本 3 supports 中文和 English。",
        }
        with (
            patch("tts.edge.edge_temp_dir", return_value=TEST_CACHE),
            patch("tts.edge._save_segment", side_effect=fake_save_segment),
        ):
            for name, text in cases.items():
                with self.subTest(name=name):
                    pcm = synthesize_edge_pcm(text=text)
                    self.assertGreater(pcm.size, 0)
                    self.assertEqual(pcm.dtype, np.float32)
                    self.assertEqual(list(TEST_CACHE.glob("edge-*.mp3")), [])

    def test_empty_text_returns_chinese_error(self):
        with self.assertRaisesRegex(EdgeTTSError, "文本不能为空"):
            split_text_safely(" \n ")

    def test_overlong_text_is_segmented_and_capped(self):
        segments = split_text_safely("这是安全分段测试。" * 300)
        self.assertGreater(len(segments), 1)
        self.assertTrue(all(len(segment) <= 280 for segment in segments))
        with self.assertRaisesRegex(EdgeTTSError, "文本过长"):
            split_text_safely("长" * 20_001)

    def test_network_unavailable_returns_chinese_error_and_cleans_temp(self):
        async def unavailable(*_args, **_kwargs):
            raise OSError("network down")

        with (
            patch("tts.edge.edge_temp_dir", return_value=TEST_CACHE),
            patch("tts.edge._save_segment", side_effect=unavailable),
            self.assertRaisesRegex(EdgeTTSError, "检查网络连接"),
        ):
            synthesize_edge_pcm(text="网络不可用测试")
        self.assertEqual(list(TEST_CACHE.glob("*")), [])

    def test_temp_filename_is_random_and_not_user_controlled(self):
        observed = []

        async def capture(segment, target, settings):
            observed.append(target.name)
            await fake_save_segment(segment, target, settings)

        dangerous_text = r"..\用户输入\secret"
        with (
            patch("tts.edge.edge_temp_dir", return_value=TEST_CACHE),
            patch("tts.edge._save_segment", side_effect=capture),
        ):
            synthesize_edge_pcm(text=dangerous_text)
        self.assertEqual(len(observed), 1)
        self.assertRegex(observed[0], r"^edge-[0-9a-f]{32}\.mp3$")
        self.assertNotIn("用户输入", observed[0])

    def test_expired_cache_cleanup_only_removes_owned_files(self):
        owned = TEST_CACHE / "edge-00000000000000000000000000000000.mp3"
        unrelated = TEST_CACHE / "keep.txt"
        owned.write_bytes(b"x")
        unrelated.write_bytes(b"x")
        old = time.time() - 7200
        os.utime(owned, (old, old))
        os.utime(unrelated, (old, old))
        self.assertEqual(cleanup_expired_cache(TEST_CACHE, 3600), 1)
        self.assertFalse(owned.exists())
        self.assertTrue(unrelated.exists())

    def test_settings_can_change_and_are_validated(self):
        settings = validate_edge_settings(
            "zh-CN-YunxiNeural", "+15%", "-10%", "+20Hz", 20
        )
        self.assertEqual(settings["rate"], "+15%")
        self.assertEqual(settings["volume"], "-10%")
        self.assertEqual(settings["pitch"], "+20Hz")
        with self.assertRaisesRegex(EdgeTTSError, "语速格式无效"):
            validate_edge_settings(rate="fast")

    def test_synthesis_failure_does_not_break_adapter(self):
        class Parent:
            def __init__(self):
                self.frames = []
                self.runtime_metrics = {"request_active": True}

            def put_audio_frame(self, frame, event):
                self.frames.append((frame, event))

        parent = Parent()
        opt = SimpleNamespace(
            fps=25,
            EDGE_TTS_VOICE="zh-CN-XiaoxiaoNeural",
            EDGE_TTS_RATE="+0%",
            EDGE_TTS_VOLUME="+0%",
            EDGE_TTS_PITCH="+0Hz",
            TTS_TIMEOUT_SECONDS=30,
            REF_FILE="",
        )
        adapter = EdgeTTS(opt, parent)
        with patch(
            "tts.edge.synthesize_edge_pcm",
            side_effect=EdgeTTSError("语音合成失败，请检查网络连接后重试"),
        ):
            adapter.txt_to_audio(("第一次失败", {}))
        self.assertEqual(parent.frames, [])
        self.assertFalse(parent.runtime_metrics["request_active"])

        with patch(
            "tts.edge.synthesize_edge_pcm",
            return_value=np.zeros(adapter.chunk * 2, dtype=np.float32),
        ):
            adapter.txt_to_audio(("第二次成功", {}))
        self.assertEqual(len(parent.frames), 2)


if __name__ == "__main__":
    unittest.main()
