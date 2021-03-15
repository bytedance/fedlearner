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
# pylint: disable=raise-missing-from

from flask_restful import Resource, reqparse
from fedlearner_webconsole.k8s_client import get_client

class SettingsApi(Resource):
    def get(self):
        res = {}

        k8s_client = get_client()
        deploy = k8s_client.get_deployment(
            'fedlearner-web-console-v2')
        res['webconsole_image'] = deploy.spec.template.spec.containers[0].image

        return {'data': res}

    def patch(self):
        parser = reqparse.RequestParser()
        parser.add_argument('webconsole_image', type=str, required=False,
                            default=None, help='image for webconsole')
        data = parser.parse_args()

        if data['webconsole_image']:
            k8s_client = get_client()
            deploy = k8s_client.get_deployment(
                'fedlearner-web-console-v2')
            deploy.spec.template.spec.containers[0].image = \
                data['webconsole_image']
            k8s_client.create_or_update_deployment(
                deploy.metadata, deploy.spec, 'fedlearner-web-console-v2')

        return {'data': {}}


def initialize_setting_apis(api):
    api.add_resource(SettingsApi, '/settings')
