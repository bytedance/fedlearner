import os
import logging
from fnmatch import fnmatch
from typing import List, Optional

import tensorflow.compat.v1 as tf


def filter_files(path: str, file_ext: Optional[str],
                 file_wildcard: Optional[str]) -> List[str]:
    files = []
    filenames = tf.io.gfile.listdir(path)
    for filename in filenames:
        _, ext = os.path.splitext(filename)
        fpath = os.path.join(path, filename)
        if tf.io.gfile.isdir(fpath):
            continue
        if file_ext and ext != file_ext:
            continue
        if file_wildcard and not fnmatch(fpath, file_wildcard):
            continue
        files.append(fpath)
    logging.info("filtered files num: ", len(files))
    return files
