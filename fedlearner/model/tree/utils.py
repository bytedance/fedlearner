import os
from fnmatch import fnmatch
from typing import List

import tensorflow.compat.v1 as tf


def filter_files(path: str, file_ext: str, file_wildcard: str) -> List[str]:
    files = []
    for dirname, _, filenames in tf.io.gfile.walk(path):
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            subdirname = os.path.join(path, os.path.relpath(dirname, path))
            fpath = os.path.join(subdirname, filename)
            if file_ext and ext != file_ext:
                continue
            if file_wildcard and not fnmatch(fpath, file_wildcard):
                continue
            files.append(fpath)
    return files
