import logging


class Visitor(object):
    def __init__(self, file_paths, batch_size=1):
        self._file_paths = file_paths
        self._batch_size = batch_size

        self._file_index = 0
        self._iter = None

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        # override for other usage
        return self._next_internal()

    def _next_internal(self):
        if self._file_index == len(self._file_paths):
            raise StopIteration
        if not self._iter:
            logging.info("Visit file %s", self._file_paths[self._file_index])
            self._iter = self.create_iter(self._file_paths[self._file_index])
        try:
            items = next(self._iter)
            return items
        except StopIteration:
            self._iter = None
            self._file_index += 1
            return self._next_internal()

    def create_iter(self, file_path):
        raise NotImplementedError
