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
from pathlib import Path

from flask_restful import Resource, reqparse
from fedlearner_webconsole.utils.decorators import jwt_required
from fedlearner_webconsole.k8s_client import get_client
from fedlearner_webconsole.utils.decorators import admin_required


_POD_NAMESPACE = 'default'
# Ref: https://stackoverflow.com/questions/46046110/
#      how-to-get-the-current-namespace-in-a-pod
_k8s_namespace_file = Path(
    '/var/run/secrets/kubernetes.io/serviceaccount/namespace')
if _k8s_namespace_file.is_file():
    _POD_NAMESPACE = _k8s_namespace_file.read_text()


class SettingsApi(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        k8s_client = get_client()
        deployment = k8s_client.get_deployment(
            name='fedlearner-web-console-v2',
            namespace=_POD_NAMESPACE)

        return {
            'data': {
                'webconsole_image':
                    deployment.spec.template.spec.containers[0].image
            }
        }

    @jwt_required()
    @admin_required
    def patch(self):
        parser = reqparse.RequestParser()
        parser.add_argument('webconsole_image', type=str, required=False,
                            default=None, help='image for webconsole')
        data = parser.parse_args()

        if data['webconsole_image']:
            new_image = data['webconsole_image']
            k8s_client = get_client()
            deployment = k8s_client.get_deployment(
                'fedlearner-web-console-v2',
                _POD_NAMESPACE)
            spec = deployment.spec
            spec.template.spec.containers[0].image = new_image
            metadata = deployment.metadata
            k8s_client.create_or_update_deployment(
                metadata=metadata,
                spec=spec,
                name=metadata.name,
                namespace=metadata.namespace)

        return {'data': {}}


def initialize_setting_apis(api):
    api.add_resource(SettingsApi, '/settings')
