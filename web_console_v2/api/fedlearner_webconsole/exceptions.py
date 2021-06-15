# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
from http import HTTPStatus
from flask import jsonify


class WebConsoleApiException(Exception):
    def __init__(self, status_code, error_code, message, details=None):
        Exception.__init__(self)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details

    def __repr__(self):
        return f'{type(self).__name__}({self.error_code} ' \
               f'{self.message}: {self.details})'

    def to_dict(self):
        dic = {
            'code': self.error_code,
            'message': self.message,
        }
        if self.details is not None:
            dic['details'] = self.details
        return dic


class InvalidArgumentException(WebConsoleApiException):
    def __init__(self, details):
        WebConsoleApiException.__init__(self, HTTPStatus.BAD_REQUEST, 400,
                                        'Invalid argument or payload.', details)


class NotFoundException(WebConsoleApiException):
    def __init__(self, message=None):
        WebConsoleApiException.__init__(
            self, HTTPStatus.NOT_FOUND, 404,
            message if message else 'Resource not found.')


class UnauthorizedException(WebConsoleApiException):
    def __init__(self, message):
        WebConsoleApiException.__init__(self, HTTPStatus.UNAUTHORIZED,
                                        401, message)


class NoAccessException(WebConsoleApiException):
    def __init__(self, message):
        WebConsoleApiException.__init__(self, HTTPStatus.FORBIDDEN,
                                        403, message)


class ResourceConflictException(WebConsoleApiException):
    def __init__(self, message):
        WebConsoleApiException.__init__(self, HTTPStatus.CONFLICT, 409, message)


class InternalException(WebConsoleApiException):
    def __init__(self, details=None):
        WebConsoleApiException.__init__(
            self, HTTPStatus.INTERNAL_SERVER_ERROR, 500,
            'Internal Error met when handling the request', details)


def make_response(exception: WebConsoleApiException):
    """Makes flask response for the exception."""
    response = jsonify(exception.to_dict())
    response.status_code = exception.status_code
    return response
