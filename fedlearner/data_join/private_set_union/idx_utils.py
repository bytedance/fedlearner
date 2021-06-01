from fedlearner.data_join.transmitter.utils import IDX


def get_skip(start_idx: IDX,
             current_idx: IDX,
             end_idx: IDX) -> int:
    """
    Calculate how many rows should be skipped according to current_idx. Note
        that in Parquet scene, we send files one by one without mixing files,
        so if start_idx.file_idx != end_idx.file_idx, all of the rows belong to
        the end_idx.file_idx's file.
    Args:
        start_idx: start IDX of the req/resp
        current_idx: current state of IDX
        end_idx: end IDX of the req/resp

    Returns:

    """
    length = end_idx.row_idx if is_new_file(start_idx, end_idx) \
        else end_idx.row_idx - start_idx.row_idx
    skip = 0 if is_new_file(start_idx, end_idx) \
        else length - (end_idx.row_idx - current_idx.row_idx)
    return skip


def is_new_file(start_idx: IDX,
                end_idx: IDX):
    return start_idx.row_idx == 0 or start_idx.file_idx < end_idx.file_idx
