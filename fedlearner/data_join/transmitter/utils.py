import typing
import queue


class ProcessException(Exception):
    pass


class _EndSentinel:
    """a sentinel for Sender's request queue"""
    pass


def _queue_iter(q: queue.Queue):
    while True:
        # use timeout to check condition rather than blocking continuously.
        # Queue object is thread-safe, no need to use Lock.
        try:
            req = q.get(timeout=5)
            if isinstance(req, _EndSentinel):
                break
            yield req
        except queue.Empty:
            pass
