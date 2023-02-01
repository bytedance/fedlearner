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

from typing import Optional

from flask_restful import Resource
from marshmallow import fields

from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.utils.decorators.pp_flask import use_kwargs
from fedlearner_webconsole.utils.flask_utils import get_current_user, make_flask_response
from fedlearner_webconsole.iam.client import get_iams


class CheckPermissionsApi(Resource):

    @credentials_required
    @use_kwargs(
        {
            'resource': fields.String(required=False, load_default=None),
            'permission': fields.String(required=False, load_default=None),
        },
        location='query',
    )
    def get(self, resource: Optional[str], permission: Optional[str]):
        """Gets all IAM policies.
        ---
        tags:
          - iam
        description: gets all IAM policies.
        responses:
          200:
            description:
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    iams:
                      description: list of policies
                      type: array
                      items:
                        type: string
        """
        user = get_current_user()
        result = get_iams(user, resource, permission)
        return make_flask_response({'iams': result})


def initialize_iams_apis(api):
    api.add_resource(CheckPermissionsApi, '/iams')
