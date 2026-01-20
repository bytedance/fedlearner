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

import os
from contextlib import contextmanager
from uuid import uuid4
from slugify import slugify
from fedlearner_webconsole.utils.pp_datetime import now
from fedlearner_webconsole.utils.file_manager import file_manager


# TODO(hangweiqiang): move Envs.STORAGE_ROOT in function
def algorithm_path(root_path: str, name: str, version: int) -> str:
    suffix = now().strftime('%Y%m%d_%H%M%S')
    return os.path.join(root_path, 'algorithms', f'{slugify(name)}-v{version}-{suffix}-{uuid4().hex[:5]}')


def algorithm_cache_path(root_path: str, algorithm_uuid: str) -> str:
    return os.path.join(root_path, 'algorithm_cache', algorithm_uuid)


def algorithm_project_path(root_path: str, name: str) -> str:
    suffix = now().strftime('%Y%m%d_%H%M%S')
    return os.path.join(root_path, 'algorithm_projects', f'{slugify(name)}-{suffix}-{uuid4().hex[:5]}')


def pending_algorithm_path(root_path: str, name: str, version: int) -> str:
    suffix = now().strftime('%Y%m%d_%H%M%S')
    return os.path.join(root_path, 'pending_algorithms', f'{slugify(name)}-v{version}-{suffix}-{uuid4().hex[:5]}')


def deleted_name(name: str) -> str:
    timestamp = now().strftime('%Y%m%d_%H%M%S')
    return f'deleted_at_{timestamp}_{name}'


@contextmanager
def check_algorithm_file(path: str):
    """clear the created algorithm files when exceptions

    Example:
        path = (the path of the algorithm files)
        with _check_algorithm_file(path):
            ...

    """
    try:
        yield
    except Exception as e:
        if os.path.exists(path):
            file_manager.remove(path)
        raise e
