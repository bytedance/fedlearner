# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
# limitations under the License.

# coding: utf-8
import logging
from functools import wraps

from flask import request

from fedlearner_webconsole.exceptions import NoAccessException
from fedlearner_webconsole.utils.const import API_VERSION
from fedlearner_webconsole.utils.flask_utils import get_current_user
from fedlearner_webconsole.iam.permission import Permission
from fedlearner_webconsole.iam.client import check


def iam_required(permission: Permission):

    def decorator(fn):

        @wraps(fn)
        def wraper(*args, **kwargs):
            if permission is None:
                return fn(*args, **kwargs)
            # remove the prefix of url (/api/v2/)
            resource_name = request.path.rpartition(API_VERSION)[-1]
            user = get_current_user()
            try:
                if not check(user.username, resource_name, permission):
                    raise NoAccessException('No permission.')
            except Exception as e:
                # defensive programming for internal errors.
                logging.error(f'Check permission failed: {user.username} ' f'{resource_name} {permission}: {str(e)}')
                raise NoAccessException('No permission.') from e
            return fn(*args, **kwargs)

        return wraper

    return decorator
