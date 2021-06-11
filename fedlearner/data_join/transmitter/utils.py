class RecvProcessException(Exception):
    pass


class _EndSentinel:
    """a sentinel for Sender's request queue"""
    pass
