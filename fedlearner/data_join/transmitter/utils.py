import typing


class ProcessException(Exception):
    pass


class _EndSentinel:
    """a sentinel for Sender's request queue"""
    pass


class PostTask:
    def __init__(self,
                 func: typing.Callable,
                 *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._func = func

    def run(self):
        self._func(*self._args, **self._kwargs)
