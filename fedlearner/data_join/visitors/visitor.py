import logging

import fedlearner.common.transmitter_service_pb2 as tsmt_pb


class Visitor(object):
    def __init__(self,
                 file_info: tsmt_pb.FileInfoList = None,
                 batch_size: int = 1):
        self._file_info = file_info
        self._batch_size = batch_size

        self._file_idx = 0
        self._iter = None

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def init(self, file_info: tsmt_pb.FileInfoList):
        self._file_info = file_info

    def next(self):
        # override for other usage
        return self._next_internal()

    def _next_internal(self):
        if self._file_idx == len(self._file_info.files):
            raise StopIteration
        if not self._iter:
            logging.info("Visit file %s", self._file_info.files[self._file_idx])
            self._iter = self.create_iter(self._file_info.files[self._file_idx])
        try:
            return next(self._iter)
        except StopIteration:
            self._iter = None
            self._file_idx += 1
            return self._next_internal()

    def create_iter(self, file_path):
        raise NotImplementedError
