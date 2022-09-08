import os
import logging
from fnmatch import fnmatch
from typing import List, Optional

import tensorflow.compat.v1 as tf


def filter_files(path: str, file_ext: Optional[str],
                 file_wildcard: Optional[str]) -> List[str]:
    files = []
    depth = 0
    for dirname, _, filenames in tf.io.gfile.walk(path):
        if depth == 2:
            break
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            subdirname = os.path.join(path, os.path.relpath(dirname, path))
            fpath = os.path.join(subdirname, filename)
            if file_ext and ext != file_ext:
                continue
            if file_wildcard and not fnmatch(fpath, file_wildcard):
                continue
            files.append(fpath)
        depth += 1
    logging.info("file wildcard is %s, file ext is %s, "
                 "filtered files num: %d", file_wildcard,
                 file_ext, len(files))
    return files
