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
import time
import signal
from functools import wraps


def raise_timeout(signum, frame):
    raise TimeoutError


def timeout_fn(time_in_second: int = 60):
    """Raise TimeoutError after time_in_second.
    Note that this decorator should be used on main thread. Found more info in
    ref: https://stackoverflow.com/questions/54749342/valueerror-signal-only-works-in-main-thread
    """

    def decorator_fn(f):

        @wraps(f)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, raise_timeout)
            signal.alarm(time_in_second)
            try:
                return f(*args, **kwargs)
            finally:
                signal.signal(signal.SIGALRM, signal.SIG_IGN)

        return wrapper

    return decorator_fn


def retry_fn(retry_times: int = 3):

    def decorator_fn(f):

        @wraps(f)
        def wrapper(*args, **kwargs):
            for i in range(retry_times - 1):
                try:
                    return f(*args, **kwargs)
                # pylint: disable=broad-except
                except Exception as e:
                    logging.exception(f'Call function {f.__name__} failed, retrying times...{i + 1}')
                    continue
            return f(*args, **kwargs)

        return wrapper

    return decorator_fn


def time_log(log_type: str = 'Function'):

    def decorator_fn(f):

        @wraps(f)
        def wrapper(*args, **kwargs):
            logging.info(f'[{log_type}] start ! ! !')
            start_time = time.time()
            res = f(*args, **kwargs)
            logging.info(f'[{log_type}] used time: {time.time() - start_time} s')
            return res

        return wrapper

    return decorator_fn
