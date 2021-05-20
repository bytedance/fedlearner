from collections import namedtuple

# NOTE: it is convenient to compare between two different IDXes
IDX = namedtuple('IDX', ['file_idx', 'row_idx'])


def _assign_idx_to_meta(meta: dict,
                        idx: IDX) -> None:
    meta['file_idx'] = idx.file_idx
    meta['row_idx'] = idx.row_idx


class RecvProcessException(Exception):
    pass


class _EndSentinel:
    """a sentinel for Sender's request queue"""
    pass
