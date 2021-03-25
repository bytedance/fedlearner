# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License

# coding=utf-8

from functools import wraps
import logging
from traceback import format_exc


def retry_fn(retry_times: int = 3, needed_exceptions=None):
    def decorator_retry_fn(f):
        # to resolve pylint warning
        # Dangerous default value [] as argument (dangerous-default-value)
        nonlocal needed_exceptions
        if needed_exceptions is None:
            needed_exceptions = [Exception]

        @wraps(f)
        def wrapper(*args, **kwargs):
            for i in range(retry_times):
                try:
                    return f(*args, **kwargs)
                except tuple(needed_exceptions):
                    logging.error(
                        'Call function failed, retrying...\nExceptions %s',
                        format_exc())
                    if i == retry_times - 1:
                        raise
                    continue

        return wrapper

    return decorator_retry_fn
