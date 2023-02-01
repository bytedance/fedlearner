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
import io
import json
import typing
import urllib.parse
from http import HTTPStatus
from typing import Optional, Tuple, Union
from flask import send_file, g, has_request_context, request
from google.protobuf.message import Message
from marshmallow import ValidationError
from webargs import fields

from envs import Envs
from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression
from fedlearner_webconsole.utils.const import SSO_HEADER
from fedlearner_webconsole.utils.filtering import parse_expression
from fedlearner_webconsole.utils.proto import to_dict


def download_json(content: dict, filename: str):
    in_memory_file = io.BytesIO()
    # `ensure_ascii=False` to make sure non-ascii show correctly
    in_memory_file.write(json.dumps(content, ensure_ascii=False).encode('utf-8'))
    in_memory_file.seek(0)
    return send_file(in_memory_file,
                     as_attachment=True,
                     attachment_filename=f'{filename}.json',
                     mimetype='application/json; charset=UTF-8',
                     cache_timeout=0)


def get_current_sso() -> Optional[str]:
    sso_headers = request.headers.get(SSO_HEADER, None)
    if sso_headers:
        return sso_headers.split()[0]
    return None


def get_current_user() -> Optional[User]:
    if has_request_context() and hasattr(g, 'current_user'):
        return g.current_user
    return None


def set_current_user(current_user: User):
    g.current_user = current_user


def _normalize_data(data: Union[Message, dict, list]) -> Union[dict, list]:
    if isinstance(data, Message):
        return to_dict(data)
    if isinstance(data, list):
        return [_normalize_data(d) for d in data]
    if isinstance(data, dict):
        return {k: _normalize_data(v) for k, v in data.items()}
    return data


def make_flask_response(data: Optional[Union[Message, dict, list]] = None,
                        page_meta: Optional[dict] = None,
                        status: int = HTTPStatus.OK) -> Tuple[dict, int]:
    if data is None:
        data = {}
    data = _normalize_data(data)

    if page_meta is None:
        page_meta = {}
    return {
        'data': data,
        'page_meta': page_meta,
    }, status


def get_link(path: str) -> str:
    host_url = None
    if has_request_context():
        host_url = request.host_url
    if not host_url:
        host_url = Envs.SERVER_HOST
    return urllib.parse.urljoin(host_url, path)


class FilterExpField(fields.Field):
    """A marshmallow field represents the filtering expression. See details in filtering.py."""

    def _deserialize(self, value: str, attr: str, data: typing.Any, **kwargs) -> FilterExpression:
        try:
            return parse_expression(value)
        except ValueError as e:
            raise ValidationError(f'Failed to parse filter {value}') from e
