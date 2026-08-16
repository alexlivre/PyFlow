"""
asyncio concurrency helpers for PyFlow.
"""

from collections import deque


class AsyncSemaphore:
    """Counting semaphore with an atomic, non-blocking acquire_nowait().

    asyncio.Semaphore only offers a blocking ``await acquire()``, which lets
    an unbounded queue of waiters pile up behind the cap (each waiting up to
    the full run timeout before a slot frees). ``acquire_nowait()`` rejects
    immediately instead, guaranteeing a 429 response on bursts. The event
    loop is single-threaded and cooperative, so the check-and-set inside
    ``acquire_nowait()`` is atomic: no await happens between reading and
    decrementing the counter.
    """

    def __init__(self, value: int = 1):
        if value < 1:
            raise ValueError("value must be >= 1")
        self._value = value

    def locked(self) -> bool:
        return self._value <= 0

    def acquire_nowait(self) -> bool:
        if self._value <= 0:
            return False
        self._value -= 1
        return True

    def release(self) -> None:
        self._value += 1
