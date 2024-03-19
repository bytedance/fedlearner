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
import queue
from multiprocessing import get_context
from typing import Optional, Callable, Any, Dict

from fedlearner_webconsole.utils.hooks import pre_start_hook


def _sub_process_wrapper(target: Optional[Callable[..., Any]], kwargs: Dict[str, Any]):
    pre_start_hook()
    target(**kwargs)


def get_result_by_sub_process(name: str, target: Optional[Callable[..., Any]], kwargs: Dict[str, Any]):
    context = get_context('spawn')
    internal_queue = context.Queue()
    kwargs['q'] = internal_queue
    wrapper_args = {'target': target, 'kwargs': kwargs}
    sub_process = context.Process(target=_sub_process_wrapper, kwargs=wrapper_args, daemon=True)
    sub_process.start()
    try:
        result = internal_queue.get(timeout=60)
    except queue.Empty as e:
        sub_process.terminate()
        raise RuntimeError(f'[subprocess] {name} task failed') from e
    finally:
        sub_process.join()
        sub_process.close()
        internal_queue.close()
    logging.info(f'[subprocess]: {name} task finished')
    return result
