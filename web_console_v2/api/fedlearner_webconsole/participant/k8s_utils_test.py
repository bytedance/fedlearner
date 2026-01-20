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

import unittest
from unittest.mock import patch, MagicMock

from fedlearner_webconsole.participant.k8s_utils import get_host_and_port, _create_or_update_participant_ingress, \
    create_or_update_participant_in_k8s
from testing.helpers import to_simple_namespace
from testing.no_web_server_test_case import NoWebServerTestCase


class ParticipantsK8sUtilsTest(NoWebServerTestCase):

    @patch('fedlearner_webconsole.participant.k8s_utils.k8s_client')
    @patch('fedlearner_webconsole.participant.k8s_utils.SettingService.get_namespace')
    def test_get_host_and_port(self, mock_get_namespace, mock_k8s_client):
        fake_service = to_simple_namespace({'spec': {'external_name': '127.0.0.10'}})
        fake_ingress = to_simple_namespace({
            'spec': {
                'rules': [{
                    'http': {
                        'paths': [{
                            'backend': {
                                'service_name': 'fakeservice',
                                'service_port': 32443
                            }
                        }]
                    }
                }]
            }
        })
        domain_name = 'test_domain_name.com'
        mock_get_namespace.return_value = 'default'
        mock_k8s_client.get_service = MagicMock(return_value=fake_service)
        mock_k8s_client.get_ingress = MagicMock(return_value=fake_ingress)

        host, port = get_host_and_port(domain_name)
        self.assertEqual(host, '127.0.0.10')
        self.assertEqual(port, 32443)
        mock_k8s_client.get_service.assert_called_once_with(name='test_domain_name', namespace='default')
        mock_k8s_client.get_ingress.assert_called_once_with(name='test_domain_name-client-auth', namespace='default')

    @patch('fedlearner_webconsole.participant.k8s_utils.k8s_client')
    def test_create_or_update_participant_ingress(self, mock_k8s_client: MagicMock):
        mock_k8s_client.create_or_update_ingress = MagicMock()
        _create_or_update_participant_ingress('fl-test', service_port=32443, namespace='fedlearner')
        mock_k8s_client.create_or_update_ingress.assert_called_once_with(
            name='fl-test-client-auth',
            namespace='fedlearner',
            metadata={
                'name': 'fl-test-client-auth',
                'namespace': 'fedlearner',
                'annotations': {
                    'nginx.ingress.kubernetes.io/backend-protocol': 'GRPCS',
                    'nginx.ingress.kubernetes.io/http2-insecure-port': 'true',
                    'nginx.ingress.kubernetes.io/configuration-snippet':
                        '\n'
                        '        grpc_next_upstream_tries 5;\n'
                        '        grpc_set_header Host test.fedlearner.net;\n'
                        '        grpc_set_header Authority test.fedlearner.net;',
                    'nginx.ingress.kubernetes.io/server-snippet':
                        '\n'
                        '        grpc_ssl_verify on;\n'
                        '        grpc_ssl_server_name on;\n'
                        '        grpc_ssl_name test.fedlearner.net;\n'
                        '        grpc_ssl_trusted_certificate /etc/ingress-nginx/client/all.pem;\n'
                        '        grpc_ssl_certificate /etc/ingress-nginx/client/client.pem;\n'
                        '        grpc_ssl_certificate_key /etc/ingress-nginx/client/client.key;'
                }
            },
            spec={
                'rules': [{
                    'host': 'fl-test-client-auth.com',
                    'http': {
                        'paths': [{
                            'pathType': 'ImplementationSpecific',
                            'backend': {
                                'serviceName': 'fl-test',
                                'servicePort': 32443
                            }
                        }]
                    }
                }],
                'ingressClassName': None
            },
        )

    @patch('fedlearner_webconsole.participant.k8s_utils._create_or_update_participant_ingress')
    @patch('fedlearner_webconsole.participant.k8s_utils.k8s_client')
    def test_create_or_update_participant_in_k8s(self, mock_k8s_client: MagicMock,
                                                 mock_create_or_update_participant_ingress: MagicMock):
        mock_k8s_client.create_or_update_service = MagicMock()
        create_or_update_participant_in_k8s(domain_name='fl-a-test.com',
                                            host='1.2.3.4',
                                            port=32443,
                                            namespace='fedlearner')
        mock_k8s_client.create_or_update_service.assert_called_once_with(
            name='fl-a-test',
            namespace='fedlearner',
            metadata={
                'name': 'fl-a-test',
                'namespace': 'fedlearner',
            },
            spec={
                'externalName': '1.2.3.4',
                'type': 'ExternalName',
            },
        )
        mock_create_or_update_participant_ingress.assert_called_once_with(
            name='fl-a-test',
            service_port=32443,
            namespace='fedlearner',
        )


if __name__ == '__main__':
    unittest.main()
