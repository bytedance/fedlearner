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
# limitations under the License.

# coding: utf-8
# pylint: disable=cyclic-import

import functools
from http import HTTPStatus
from flask import request
from flask_restful import Resource, reqparse
from flask_jwt_extended.utils import get_current_user
from flask_jwt_extended import jwt_required, create_access_token

from fedlearner_webconsole.db import db
from fedlearner_webconsole.auth.models import (State, User, Role,
                                               MUTABLE_ATTRS_MAPPER)
from fedlearner_webconsole.exceptions import (NotFoundException,
                                              InvalidArgumentException,
                                              ResourceConflictException,
                                              UnauthorizedException)

from fedlearner_webconsole.mmgr.models import ModelModel


class ModelApi(Resource):
    def post(self, op):
        obj = request.get_json(force=True)
        if op == "new": return ModelMgr().new(obj)
        return {"op": op, "obj": obj}, HTTPStatus.BAD_REQUEST


class ModelMgr:
    def new(self, obj):
        modelID = obj["modelID"]
        ModelModel().new(modelID)
        return {
                   "modelID": modelID
               }, HTTPStatus.OK


def initialize_mmgr_apis(api):
    api.add_resource(ModelApi, '/model/<string:op>')
