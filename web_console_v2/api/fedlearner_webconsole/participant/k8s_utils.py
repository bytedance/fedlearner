# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import re
from typing import Tuple, List, Dict

from envs import Envs
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.k8s.k8s_client import k8s_client
from fedlearner_webconsole.utils.domain_name import get_pure_domain_name

_RE_INGRESS_NAME = re.compile(r'^(fl-).+(-client-auth)$')
_RE_SERVICE_NAME = re.compile(r'^(fl-).+$')


def get_valid_candidates() -> Dict[str, List[str]]:
    with db.session_scope() as session:
        namespace = SettingService(session).get_namespace()
    ingresses = k8s_client.list_ingress(namespace)
    ingress_names = []
    for ingress in ingresses.items:
        if hasattr(ingress, 'metadata') and hasattr(ingress.metadata, 'name'):
            name = ingress.metadata.name
            if _RE_INGRESS_NAME.fullmatch(name):
                ingress_names.append(name)

    services = k8s_client.list_service(namespace)
    service_names = []
    for service in services.items:
        if hasattr(service, 'metadata') and hasattr(service.metadata, 'name'):
            name = service.metadata.name
            if _RE_SERVICE_NAME.fullmatch(name):
                service_names.append(name)

    candidates = [{'domain_name': f'{name[:-12]}.com'} for name in ingress_names if name[:-12] in service_names]
    return candidates


def get_host_and_port(domain_name: str) -> Tuple[str, int]:
    with db.session_scope() as session:
        namespace = SettingService(session).get_namespace()
    service_name = domain_name.rpartition('.')[0]
    ingress_name = f'{service_name}-client-auth'

    try:
        service = k8s_client.get_service(name=service_name, namespace=namespace)
        ingress = k8s_client.get_ingress(name=ingress_name, namespace=namespace)
        host = service.spec.external_name
        port = ingress.spec.rules[0].http.paths[0].backend.service_port
    except Exception as e:
        raise InvalidArgumentException(details=f'can not find post or port in ingress, {e}') from e

    return host, port


def _create_or_update_participant_ingress(name: str, service_port: int, namespace: str):
    client_auth_ingress_name = f'{name}-client-auth'
    pure_domain_name = get_pure_domain_name(name)
    host = f'{pure_domain_name}.fedlearner.net'
    configuration_snippet = f"""
        grpc_next_upstream_tries 5;
        grpc_set_header Host {host};
        grpc_set_header Authority {host};"""
    # TODO(wangsen.0914): removes this hack after we align the controller
    is_tce = False  # TODO(lixiaoguang.01) hardcode
    secret_path = 'ingress-nginx/client' if not is_tce else 'tce_static/bdcert'
    grpc_ssl_trusted_certificate = 'all.pem' if not is_tce else 'intermediate.pem'
    server_snippet = f"""
        grpc_ssl_verify on;
        grpc_ssl_server_name on;
        grpc_ssl_name {host};
        grpc_ssl_trusted_certificate /etc/{secret_path}/{grpc_ssl_trusted_certificate};
        grpc_ssl_certificate /etc/{secret_path}/client.pem;
        grpc_ssl_certificate_key /etc/{secret_path}/client.key;"""
    # yapf: disable
    k8s_client.create_or_update_ingress(metadata={
        'name': client_auth_ingress_name,
        'namespace': namespace,
        'annotations': {
            'nginx.ingress.kubernetes.io/backend-protocol': 'GRPCS',
            'nginx.ingress.kubernetes.io/http2-insecure-port': 'true',
            'nginx.ingress.kubernetes.io/configuration-snippet': configuration_snippet,
            'nginx.ingress.kubernetes.io/server-snippet': server_snippet
        }
    },
        spec={
            'rules': [{
                'host': f'{client_auth_ingress_name}.com',
                'http': {
                    'paths': [{
                        'pathType': 'ImplementationSpecific',
                        'backend': {
                            'serviceName': name,
                            'servicePort': service_port
                        }
                    }]
                }
            }],
            'ingressClassName': None
        },
        name=client_auth_ingress_name,
        namespace=namespace)
    # yapf: enable


def create_or_update_participant_in_k8s(domain_name: str, host: str, port: int, namespace: str):
    name = domain_name.rpartition('.')[0]
    k8s_client.create_or_update_service(
        metadata={
            'name': name,
            'namespace': namespace,
        },
        spec={
            'externalName': host,
            'type': 'ExternalName',
        },
        name=name,
        namespace=namespace,
    )
    _create_or_update_participant_ingress(name=name, service_port=port, namespace=namespace)
