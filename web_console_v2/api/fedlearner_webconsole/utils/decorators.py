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

from fedlearner_webconsole.exceptions import NeedToRetryException

def retry_fn(retry_times: int = 3):
    def decorator_retry_fn(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            fallback_ret_value = None
            for _ in range(retry_times):
                try:
                    return f(*args, **kwargs)
                except NeedToRetryException as err:
                    fallback_ret_value = err.ret_value
                    continue
            return fallback_ret_value
        return wrapper
    return decorator_retry_fn
