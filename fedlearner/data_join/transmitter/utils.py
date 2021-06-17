import typing


class ProcessException(Exception):
    pass


class _EndSentinel:
    """a sentinel for Sender's request queue"""
    pass


class PostTask:
    def __init__(self,
                 func: typing.Callable,
                 args: typing.List = None,
                 kwargs: typing.Dict = None):
        self._args = args or []
        self._kwargs = kwargs or {}
        self._func = func

    def run(self):
        self._func(*self._args, **self._kwargs)
