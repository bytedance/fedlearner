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

import re
from functools import wraps
from flask import request
from marshmallow import EXCLUDE
from webargs.flaskparser import FlaskParser

from fedlearner_webconsole.utils.flask_utils import get_current_user
from fedlearner_webconsole.auth.models import Role
from fedlearner_webconsole.exceptions import InvalidArgumentException, \
    UnauthorizedException

# TODO(xiangyuxuan.prs): valid Kubernetes Object with its own regex
# [DNS Subdomain Names](https://kubernetes.io/docs/concepts/overview/working-with-objects/names/)
# Regex to match the pattern:
# Start/end with English/Chinese characters or numbers
# other content could be English/Chinese character, -, _ or numbers
# Max length 64
UNIVERSAL_NAME_PATTERN = r'^[a-zA-Z0-9\u4e00-\u9fa5]' \
                         r'[a-zA-Z0-9\u4e00-\u9fa5\-_\.]' \
                         r'{0,62}[a-zA-Z0-9\u4e00-\u9fa5]$'
MAX_COMMENT_LENGTH = 200


def admin_required(f):

    @wraps(f)
    def wrapper_inside(*args, **kwargs):
        current_user = get_current_user()
        if current_user.role != Role.ADMIN:
            raise UnauthorizedException('only admin can operate this')
        return f(*args, **kwargs)

    return wrapper_inside


def input_validator(f):

    @wraps(f)
    def wrapper_inside(*args, **kwargs):
        if hasattr(request, 'content_type') and request.content_type.startswith('multipart/form-data'):
            params = request.form
        else:
            params = request.get_json() or {}
        name = params.get('name', None)
        comment = params.get('comment', '')
        if name is not None:
            _validate_name(name)
        if comment:
            _validate_comment(comment)
        return f(*args, **kwargs)

    return wrapper_inside


def _validate_name(name: str):
    if re.match(UNIVERSAL_NAME_PATTERN, name) is None:
        raise InvalidArgumentException(f'Invalid name {name}: Must start/end'
                                       f' with uppercase and lowercase letters,'
                                       f' numbers or Chinese characters, could'
                                       f' contain - or _ in the middle, and '
                                       f'max length is 63 characters. ')


def _validate_comment(comment: str):
    if len(comment) > MAX_COMMENT_LENGTH:
        raise InvalidArgumentException(f'Input comment too long, max length' f' is {MAX_COMMENT_LENGTH}')


# Ref: https://webargs.readthedocs.io/en/latest/advanced.html#default-unknown
class _Parser(FlaskParser):
    DEFAULT_UNKNOWN_BY_LOCATION = {'query': EXCLUDE, 'json': EXCLUDE, 'form': EXCLUDE}


parser = _Parser()
use_args = parser.use_args
use_kwargs = parser.use_kwargs
