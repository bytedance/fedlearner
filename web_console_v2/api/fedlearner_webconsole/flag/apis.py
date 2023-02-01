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

#   coding: utf-8
from http import HTTPStatus

from flask_restful import Resource, Api
from fedlearner_webconsole.flag.models import get_flags


class FlagsApi(Resource):

    def get(self):
        """Get flags
        ---
        tags:
          - flag
        responses:
          200:
            description: Flags are returned
            content:
              application/json:
                schema:
                  type: object
                  additionalProperties: true
                  example:
                    FLAG_1: string_value
                    FLAG_2: true
                    FLAG_3: 1
        """
        return {'data': get_flags()}, HTTPStatus.OK


def initialize_flags_apis(api: Api):
    api.add_resource(FlagsApi, '/flags')
