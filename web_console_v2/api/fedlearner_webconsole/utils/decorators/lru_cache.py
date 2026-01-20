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

import functools
from datetime import datetime, timedelta


# TODO(xiangyuxuan): use custom lru to implement cache_clear(key)
def lru_cache(timeout: int = 600, maxsize: int = 10000):
    """Extension of functools lru_cache with a timeout.

    Notice!: Do not use this decorator in class methods, or it will leak memory.
    https://stackoverflow.com/questions/1227121/
    compare-object-instances-for-equality-by-their-attributes

    Args:
        timeout (int): Timeout in seconds to clear the WHOLE cache, default = 10 minutes
        maxsize (int): Maximum Size of the Cache
    """

    def wrapper_cache(func):
        func = functools.lru_cache(maxsize=maxsize)(func)
        func.delta = timedelta(seconds=timeout)
        func.expiration = datetime.utcnow() + func.delta

        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            if datetime.utcnow() >= func.expiration:
                func.cache_clear()
                func.expiration = datetime.utcnow() + func.delta

            return func(*args, **kwargs)

        wrapped_func.cache_clear = func.cache_clear
        return wrapped_func

    return wrapper_cache
