"""Thread-safe queue helpers shared by media, ASR and TTS pipelines."""

import queue
from typing import Any


def drain_queue(target: queue.Queue[Any]) -> int:
    """Remove every queued item using the public API.

    ``Queue.get_nowait`` updates the queue's internal condition variables,
    unlike clearing ``queue.queue`` directly.  This means a producer blocked
    in ``put`` is woken as soon as interruption frees capacity.
    """

    removed = 0
    while True:
        try:
            target.get_nowait()
        except queue.Empty:
            return removed
        else:
            removed += 1
            target.task_done()
