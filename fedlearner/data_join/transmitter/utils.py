import typing
import queue


class ProcessException(Exception):
    pass


class _EndSentinel:
    """a sentinel for Sender's request queue"""
    pass


class PostProcessJob:
    def __init__(self,
                 func: typing.Callable,
                 *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._func = func

    def run(self):
        self._func(*self._args, **self._kwargs)


def _queue_iter(q: queue.Queue, stop_cond):
    while not stop_cond():
        # use timeout to check condition rather than blocking continuously.
        # Queue object is thread-safe, no need to use Lock.
        try:
            req = q.get(timeout=5)
            if isinstance(req, _EndSentinel):
                break
            yield req
        except queue.Empty:
            pass
