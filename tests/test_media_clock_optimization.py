import queue
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from server.webrtc import PlayerStreamTrack, VIDEO_TIME_BASE
from utils.queues import drain_queue


class QueueDrainTests(unittest.TestCase):
    def test_drain_queue_wakes_blocked_producer(self):
        target = queue.Queue(maxsize=1)
        target.put("old")
        finished = threading.Event()

        def produce():
            target.put("new")
            finished.set()

        producer = threading.Thread(target=produce)
        producer.start()
        self.assertFalse(finished.wait(0.05))

        self.assertEqual(drain_queue(target), 1)
        self.assertTrue(finished.wait(1))
        producer.join(1)
        self.assertEqual(target.get_nowait(), "new")


class MediaClockTests(unittest.IsolatedAsyncioTestCase):
    async def test_video_pts_remain_monotonic_after_starvation_rebase(self):
        metrics = {}
        player = SimpleNamespace(
            set_metric=lambda name, value: metrics.__setitem__(name, value),
            get_metric=lambda name, default=None: metrics.get(name, default),
        )
        track = PlayerStreamTrack(player, kind="video")

        with (
            patch(
                "server.webrtc.time.perf_counter",
                side_effect=[100.0, 100.04, 101.0],
            ),
            patch("server.webrtc.asyncio.sleep", new=AsyncMock()),
        ):
            first_pts, first_base = await track.next_timestamp()
            second_pts, second_base = await track.next_timestamp()
            third_pts, third_base = await track.next_timestamp()

        self.assertEqual((first_base, second_base, third_base), (VIDEO_TIME_BASE,) * 3)
        self.assertEqual((first_pts, second_pts, third_pts), (0, 3600, 7200))
        self.assertEqual(metrics["media_clock_rebases"], 1)
        self.assertGreater(metrics["media_max_late_ms"], 800)


if __name__ == "__main__":
    unittest.main()
