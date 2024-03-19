# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
from typing import Optional, Callable

import time
from functools import wraps


def _default_need_retry(unused_exception: Exception) -> bool:
    del unused_exception
    # Retry for all exceptions
    return True


def retry_fn(retry_times: int = 3,
             delay: int = 0,
             backoff: float = 1.0,
             need_retry: Optional[Callable[[Exception], bool]] = None):
    """A function to generate a decorator for retry.

    Args:
        retry_times: Times to try.
        delay: Intervals in milliseconds between attempts, default is 0 (no delay).
        backoff: Multiplier on the delay between attempts, default is 1. For example, if delay is set to 1000,
            and backoff is 2, then the first retry will be delayed 1000ms, and second one will be 2000ms,
            third one will be 4000ms.
        need_retry: A callable function to check if the raised exception will trigger retry or not.
    """

    def decorator_retry_fn(f):
        nonlocal need_retry
        if need_retry is None:
            # By default retry for all exceptions
            need_retry = _default_need_retry

        @wraps(f)
        def wrapper(*args, **kwargs):  # pylint: disable=inconsistent-return-statements
            nonlocal delay
            # NOTE: a local variable for delay is a MUST-HAVE, if you reuse the delay in the parameter,
            # it will be accumulated for all function executions.
            local_delay = delay
            for i in range(retry_times):
                try:
                    return f(*args, **kwargs)
                except Exception as e:  # pylint: disable=broad-except
                    # Re-raise if there is no need for retry
                    if not need_retry(e):
                        raise
                    logging.exception(
                        f'Call function failed, retrying {i + 1} times...\n'
                        f'function name is {f.__name__}, args are {repr(args)}, kwargs are {repr(kwargs)}')
                    if i == retry_times - 1:
                        raise
                    if local_delay > 0:
                        time.sleep(local_delay / 1000.0)
                        local_delay = local_delay * backoff

        return wrapper

    return decorator_retry_fn
