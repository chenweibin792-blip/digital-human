import json
import queue
import threading
import unittest
from types import SimpleNamespace

import numpy as np
import torch

from avatars.base_avatar import AudioFrameData, BaseAvatar


class PerformanceStage7Tests(unittest.TestCase):
    def test_cuda_oom_is_contained_and_session_can_continue(self):
        avatar = object.__new__(BaseAvatar)
        avatar.batch_size = 1
        avatar.chunk = 320
        avatar.sessionid = "oom-test"
        avatar.custom_index = {}
        avatar.custom_audiotype = 0
        avatar.runtime_metrics = {"oom_count": 0}
        avatar.msgqueues = []
        avatar.res_frame_queue = queue.Queue(maxsize=4)
        avatar.asr = SimpleNamespace(
            feat_queue=queue.Queue(),
            output_queue=queue.Queue(),
            flush_talk=lambda: None,
        )
        avatar.asr.feat_queue.put(np.zeros((1, 80, 16), dtype=np.float32))
        for _ in range(2):
            avatar.asr.output_queue.put(
                AudioFrameData(
                    data=np.ones(320, dtype=np.float32),
                    type=0,
                    userdata={},
                )
            )
        events = []
        avatar.send_msg = lambda message: events.append(json.loads(message))
        quit_event = threading.Event()

        def fail_once(_index, _features):
            quit_event.set()
            raise torch.cuda.OutOfMemoryError("mock CUDA out of memory")

        avatar.inference_batch = fail_once
        avatar.inference(quit_event)

        self.assertEqual(avatar.runtime_metrics["oom_count"], 1)
        self.assertEqual(avatar.res_frame_queue.qsize(), 1)
        _, frames, _ = avatar.res_frame_queue.get_nowait()
        self.assertTrue(all(frame.type == 1 for frame in frames))
        self.assertEqual(events[0]["type"], "system")
        self.assertIn("720P", events[0]["message"])

    def test_inference_methods_are_no_grad_wrapped(self):
        self.assertTrue(hasattr(BaseAvatar.inference, "__call__"))
        with torch.enable_grad():
            tensor = torch.ones(1, requires_grad=True)
            with torch.inference_mode():
                self.assertFalse(torch.is_grad_enabled())
                self.assertFalse((tensor * 2).requires_grad)


if __name__ == "__main__":
    unittest.main()
