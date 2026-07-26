import asyncio
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from avatars.audio_features.base_asr import BaseASR
from llm import LLMCancelled, LLMError, LLMSettings, OpenAICompatibleLLM
from server.rtc_manager import RTCManager
from server.session_manager import MaxSessionError, SessionManager
from tts.base_tts import BaseTTS, State


class SessionManagerStage6Tests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.manager = SessionManager()
        self.manager.sessions.clear()
        self.manager.set_max_session(1)

    async def asyncTearDown(self):
        self.manager.sessions.clear()

    async def test_concurrent_creation_respects_single_session_limit(self):
        def builder(sessionid, _params):
            time.sleep(0.15)
            return SimpleNamespace(sessionid=sessionid, flush_talk=lambda: None)

        self.manager.init_builder(builder)
        results = await asyncio.gather(
            self.manager.create_session({}, "one"),
            self.manager.create_session({}, "two"),
            return_exceptions=True,
        )
        self.assertEqual(sum(isinstance(item, str) for item in results), 1)
        self.assertEqual(sum(isinstance(item, MaxSessionError) for item in results), 1)
        self.assertEqual(len(self.manager.sessions), 1)

    async def test_failed_builder_does_not_leave_placeholder(self):
        def builder(_sessionid, _params):
            raise RuntimeError("build failed")

        self.manager.init_builder(builder)
        with self.assertRaisesRegex(RuntimeError, "build failed"):
            await self.manager.create_session({}, "broken")
        self.assertNotIn("broken", self.manager.sessions)

    async def test_rtc_close_stops_player_and_handles_reentrant_callback(self):
        rtc = RTCManager(SimpleNamespace())
        stopped = []

        class Track:
            def __init__(self, name):
                self.name = name

            def stop(self):
                stopped.append(self.name)

        player = SimpleNamespace(audio=Track("audio"), video=Track("video"))

        class Peer:
            connectionState = "connected"

            async def close(self):
                await rtc.close_session("lifecycle")
                self.connectionState = "closed"

        avatar = SimpleNamespace(flush_talk=lambda: stopped.append("flush"))
        self.manager.sessions["lifecycle"] = avatar
        rtc.session_players["lifecycle"] = player
        rtc.session_pcs["lifecycle"] = Peer()
        rtc.pcs.add(rtc.session_pcs["lifecycle"])

        await rtc.close_session("lifecycle")

        self.assertEqual(stopped, ["audio", "video", "flush"])
        self.assertNotIn("lifecycle", self.manager.sessions)
        self.assertNotIn("lifecycle", rtc.session_players)
        self.assertNotIn("lifecycle", rtc.session_pcs)
        self.assertFalse(rtc.closing_sessions)


class QueueAndLLMStage6Tests(unittest.TestCase):
    def test_tts_and_asr_flush_are_queue_safe(self):
        opt = SimpleNamespace(fps=25, batch_size=2, l=1, r=1)
        tts = BaseTTS(opt, None)
        tts.msgqueue.put(("first", {}))
        tts.msgqueue.put(("second", {}))
        tts.flush_talk()
        self.assertEqual(tts.msgqueue.qsize(), 0)
        self.assertEqual(tts.state, State.PAUSE)

        asr = BaseASR(opt)
        asr.put_audio_frame([0.0] * 320, {})
        asr.flush_talk()
        self.assertEqual(asr.queue.qsize(), 0)

    def settings(self):
        return LLMSettings(
            provider="openai_compatible",
            base_url="http://127.0.0.1:1/v1",
            api_key="mock-key",
            model="mock",
            timeout_seconds=3,
            max_retries=0,
            temperature=0.7,
            max_history_turns=10,
            stream=True,
            system_prompt="test",
        )

    def test_same_session_rejects_overlapping_generation(self):
        service = OpenAICompatibleLLM(self.settings(), client=SimpleNamespace())
        lock = service._session_lock("same")
        lock.acquire()
        try:
            with self.assertRaises(LLMError) as caught:
                service.generate("same", "second")
            self.assertEqual(caught.exception.code, "session_busy")
        finally:
            lock.release()

    def test_cancel_stops_stream_before_history_or_tts(self):
        def chunks():
            for index in range(20):
                time.sleep(0.03)
                yield SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            delta=SimpleNamespace(content=f"片段{index}"),
                            finish_reason=None,
                        )
                    ]
                )

        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=Mock(side_effect=lambda **_: chunks()))
            )
        )
        service = OpenAICompatibleLLM(self.settings(), client=client)
        result = {}

        def run():
            try:
                service.generate("cancel-me", "长回答")
            except Exception as exc:
                result["error"] = exc

        thread = threading.Thread(target=run)
        thread.start()
        time.sleep(0.12)
        service.cancel_session("cancel-me")
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertIsInstance(result.get("error"), LLMCancelled)
        self.assertEqual(service.get_history("cancel-me"), [])


if __name__ == "__main__":
    unittest.main()
