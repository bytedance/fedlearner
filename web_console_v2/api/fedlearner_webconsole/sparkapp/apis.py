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
import base64
from http import HTTPStatus

from flask import request
from flask_restful import Api, Resource

from fedlearner_webconsole.sparkapp.schema import SparkAppConfig
from fedlearner_webconsole.utils.decorators import jwt_required
from fedlearner_webconsole.sparkapp.service import SparkAppService
from fedlearner_webconsole.exceptions import (InvalidArgumentException,
                                              NotFoundException)


class SparkAppsApi(Resource):
    @jwt_required()
    def post(self):
        service = SparkAppService()
        data = request.json

        try:
            config = SparkAppConfig.from_dict(data)
            if config.files:
                config.files = base64.b64decode(config.files)
        except ValueError as err:
            raise InvalidArgumentException(details=err)

        res = service.submit_sparkapp(config=config)
        return {'data': res.to_dict()}, HTTPStatus.CREATED


class SparkAppApi(Resource):
    @jwt_required()
    def get(self, sparkapp_name: str):
        service = SparkAppService()
        return {
            'data': service.get_sparkapp_info(sparkapp_name).to_dict()
        }, HTTPStatus.OK

    @jwt_required()
    def delete(self, sparkapp_name: str):
        service = SparkAppService()
        try:
            sparkapp_info = service.delete_sparkapp(sparkapp_name)
            return {'data': sparkapp_info.to_dict()}, HTTPStatus.OK
        except NotFoundException:
            return {'data': {'name': sparkapp_name}}, HTTPStatus.OK


def initialize_sparkapps_apis(api: Api):
    api.add_resource(SparkAppsApi, '/sparkapps')
    api.add_resource(SparkAppApi, '/sparkapps/<string:sparkapp_name>')
