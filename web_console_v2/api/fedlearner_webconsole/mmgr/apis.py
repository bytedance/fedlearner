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
import json
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

from fedlearner_webconsole.mmgr.models import *


class ModelApi(Resource):
    def post(self, op):
        obj = request.get_json(force=True)
        return self.__getattribute__(f"op_{op}")(obj)
        # return {"op": op, "obj": obj}, HTTPStatus.BAD_REQUEST

    def op_new(self, obj):
        modelID = str(obj["modelID"])
        ModelMgr().new(modelID)
        return {
                   "modelID": modelID
               }, HTTPStatus.OK

    def op_query(self, obj):
        modelID = str(obj["modelID"])
        o = ModelMgr().query(modelID)
        return {
                   "modelID": o.modelID
               } if o else None, HTTPStatus.OK


class ModelMgr:
    def new(self, modelID):
        model = ModelModel()

        model.modelID = modelID
        model.state = json.dumps({
            "state": "PENDING"
        })
        model.commit()

        # TODO start

        model.state = json.dumps({
            "state": "COMMITTED"
        })
        model.commit()

    def query(self, modelID):
        return queryModel(modelID)


def initialize_mmgr_apis(api):
    api.add_resource(ModelApi, "/model/<string:op>")
