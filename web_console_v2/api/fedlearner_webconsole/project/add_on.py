# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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

import tarfile
import io
import os
from base64 import b64encode, b64decode
from typing import Type, Dict
from OpenSSL import crypto, SSL
from fedlearner_webconsole.utils.k8s_client import K8sClient

CA_SECRET_NAME = 'ca-secret'
OPERATOR_NAME = 'fedlearner-operator'
SERVER_SECRET_NAME = 'fedlearner-proxy-server'
INGRESS_NGINX_CONTROLLER_NAME = 'fedlearner-stack-ingress-nginx-controller'


def parse_certificates(encoded_gz):
    """
    Parse certificates from base64-encoded string to a dict
    Args:
        encoded_gz: A base64-encoded string from a `.gz` file.
    Returns:
        dict: key is the file name, value is the content
    """
    binary_gz = io.BytesIO(b64decode(encoded_gz))
    with tarfile.open(fileobj=binary_gz) as gz:
        certificates = {}
        for file in gz.getmembers():
            if file.isfile():
                # raw file name is like `fl-test.com/client/client.pem`
                certificates[file.name.split('/', 1)[-1]] = \
                    str(b64encode(gz.extractfile(file).read()),
                        encoding='utf-8')
    return certificates


def verify_certificates(certificates: Dict[str, str]) -> (bool, str):
    """
    Verify certificates from 4 aspects:
    1. The CN of all public keys are equal.
    2. All the CN are generic domain names.
    3. Public key match private key.
    4. Private key is signed by CA.
    Args:
        certificates:
    Returns:
    """
    try:
        client_public_key = crypto.load_certificate(
            crypto.FILETYPE_PEM,
            b64decode(certificates.get('client/client.pem')))
        server_public_key = crypto.load_certificate(
            crypto.FILETYPE_PEM,
            b64decode(certificates.get('server/server.pem')))
        client_private_key = crypto.load_privatekey(
            crypto.FILETYPE_PEM,
            b64decode(certificates.get('client/client.key')))
        server_private_key = crypto.load_privatekey(
            crypto.FILETYPE_PEM,
            b64decode(certificates.get('server/server.key')))
        client_intermediate_ca = crypto.load_certificate(
            crypto.FILETYPE_PEM,
            b64decode(certificates.get('client/intermediate.pem')))
        server_intermediate_ca = crypto.load_certificate(
            crypto.FILETYPE_PEM,
            b64decode(certificates.get('server/intermediate.pem')))
        client_root_ca = crypto.load_certificate(
            crypto.FILETYPE_PEM,
            b64decode(certificates.get('client/root.pem')))
        server_root_ca = crypto.load_certificate(
            crypto.FILETYPE_PEM,
            b64decode(certificates.get('server/root.pem')))
    except crypto.Error as err:
        return False, 'Format of key or CA is invalid: {}'.format(err)

    if client_public_key.get_subject().CN != server_public_key.get_subject().CN:
        return False, 'Client and server public key CN mismatch'
    if not client_public_key.get_subject().CN.startswith('*.'):
        return False, 'CN of public key should be a generic domain name'

    try:
        client_context = SSL.Context(SSL.TLSv1_METHOD)
        client_context.use_certificate(client_public_key)
        client_context.use_privatekey(client_private_key)
        client_context.check_privatekey()

        server_context = SSL.Context(SSL.TLSv1_METHOD)
        server_context.use_certificate(server_public_key)
        server_context.use_privatekey(server_private_key)
        server_context.check_privatekey()
    except SSL.Error as err:
        return False, 'Key pair mismatch: {}'.format(err)

    try:
        client_store = crypto.X509Store()
        client_store.add_cert(client_root_ca)
        client_store.add_cert(client_intermediate_ca)
        crypto.X509StoreContext(client_store, client_public_key)\
            .verify_certificate()
    except crypto.X509StoreContextError as err:
        return False, 'Client key and CA mismatch: {}'.format(err)
    try:
        server_store = crypto.X509Store()
        server_store.add_cert(server_root_ca)
        server_store.add_cert(server_intermediate_ca)
        crypto.X509StoreContext(server_store, server_public_key)\
            .verify_certificate()
    except crypto.X509StoreContextError as err:
        return False, 'Server key and CA mismatch: {}'.format(err)

    return True, ''


def create_add_on(client: Type[K8sClient], domain_name: str, url: str,
                  certificates: Dict[str, str], custom_host: str = None):
    """
    Idempotent
    Create add on and upgrade nginx-ingress and operator.
    If add on of domain_name exists, replace it.

    Args:
        client:       K8s client instance
        domain_name:  participant's domain name, used to create Ingress
        url:          participant's external ip, used to create ExternalName
                      Service
        certificates: used for two-way tls authentication and to create one
                      server Secret, one client Secret and one CA
        custom_host:  used for case where participant is using an external
                      authentication gateway
    """
    # url: xxx.xxx.xxx.xxx:xxxxx
    ip = url.split(':')[0]
    port = int(url.split(':')[1])
    client_all_pem = str(b64encode('{}\n{}'.format(
        str(b64decode(certificates.get('client/intermediate.pem')),
            encoding='utf-8').strip(),
        str(b64decode(certificates.get('client/root.pem')),
            encoding='utf-8').strip()).encode()), encoding='utf-8')
    server_all_pem = str(b64encode('{}\n{}'.format(
        str(b64decode(certificates.get('server/intermediate.pem')),
            encoding='utf-8').strip(),
        str(b64decode(certificates.get('server/root.pem')),
            encoding='utf-8').strip()).encode()), encoding='utf-8')
    name = domain_name.split('.')[0]
    client_secret_name = '{}-client'.format(name)
    client_auth_ingress_name = '-client-auth.'.join(domain_name.split('.'))

    # Create server certificate secret
    # If users verify gRpc in external gateway,
    # `AUTHORIZATION_MODE` should be set to `EXTERNAL`.
    if os.environ.get('AUTHORIZATION_MODE') != 'EXTERNAL':
        client.create_or_update_secret(
            data={
                'ca.crt': certificates.get('server/intermediate.pem'),
                'tls.crt': certificates.get('server/server.pem'),
                'tls.key': certificates.get('server/server.key')
            },
            metadata={
                'name': SERVER_SECRET_NAME,
                'namespace': 'default'
            },
            secret_type='Opaque',
            name=SERVER_SECRET_NAME
        )
        client.create_or_update_secret(
            data={
                'ca.crt': server_all_pem
            },
            metadata={
                'name': CA_SECRET_NAME,
                'namespace': 'default'
            },
            secret_type='Opaque',
            name=CA_SECRET_NAME
        )
        # TODO: Support multiple participants
        operator = client.get_deployment(OPERATOR_NAME)
        new_args = list(filter(lambda arg: not arg.startswith('--ingress'),
                               operator.spec.template.spec.containers[0].args))
        new_args.extend([
            '--ingress-extra-host-suffix=".{}"'.format(domain_name),
            '--ingress-client-auth-secret-name="default/ca-secret"',
            '--ingress-enabled-client-auth=true',
            '--ingress-secret-name={}'.format(SERVER_SECRET_NAME)])
        operator.spec.template.spec.containers[0].args = new_args
        client.create_or_update_deployment(metadata=operator.metadata,
                                           spec=operator.spec,
                                           name=OPERATOR_NAME)

        # Create client certificate secret
        client.create_or_update_secret(
            data={
                'client.pem': certificates.get('client/intermediate.pem'),
                'client.key': certificates.get('client/client.key'),
                'all.pem': client_all_pem
            },
            metadata={
                'name': client_secret_name
            },
            secret_type='Opaque',
            name=client_secret_name
        )

        # Update ingress-nginx-controller to load client secret
        ingress_nginx_controller = client.get_deployment(
            INGRESS_NGINX_CONTROLLER_NAME
        )
        volumes = ingress_nginx_controller.spec.template.spec.volumes or []
        volumes = list(filter(lambda volume: volume.name != client_secret_name,
                              volumes))
        volumes.append({
            'name': client_secret_name,
            'secret': {
                'secretName': client_secret_name
            }
        })
        volume_mounts = ingress_nginx_controller.spec.template\
                            .spec.containers[0].volume_mounts or []
        volume_mounts = list(filter(
            lambda mount: mount.name != client_secret_name, volume_mounts))
        volume_mounts.append(
            {
                'mountPath': '/etc/{}/client/'.format(name),
                'name': client_secret_name
            })
        ingress_nginx_controller.spec.template.spec.volumes = volumes
        ingress_nginx_controller.spec.template\
            .spec.containers[0].volume_mounts = volume_mounts
        client.create_or_update_deployment(
            metadata=ingress_nginx_controller.metadata,
            spec=ingress_nginx_controller.spec,
            name=INGRESS_NGINX_CONTROLLER_NAME
        )
        # TODO: check ingress-nginx-controller's health

    # Create ingress to forward request to peer
    client.create_or_update_service(
        metadata={
            'name': name,
            'namespace': 'default'
        },
        spec={
            'externalName': ip,
            'type': 'ExternalName'
        },
        name=name
    )
    configuration_snippet_template = 'grpc_next_upstream_tries 5;\n'\
                                     'grpc_set_header Host {0};\n'\
                                     'grpc_set_header Authority {0};'
    configuration_snippet = \
        configuration_snippet_template.format(custom_host or '$http_x_host')
    client.create_or_update_ingress(
        metadata={
            'name': domain_name,
            'namespace': 'default',
            'annotations': {
                'kubernetes.io/ingress.class': 'nginx',
                'nginx.ingress.kubernetes.io/backend-protocol': 'GRPCS',
                'nginx.ingress.kubernetes.io/http2-insecure-port': 't',
                'nginx.ingress.kubernetes.io/configuration-snippet':
                configuration_snippet
            }
        },
        spec={
            'rules': [{
                'host': domain_name,
                'http': {
                    'paths': [
                        {
                            'path': '/',
                            'backend': {
                                'serviceName': name,
                                'servicePort': port
                            }
                        }
                    ]
                }
            }]
        },
        name=domain_name
    )
    server_snippet_template = \
        'grpc_ssl_verify on;\n'\
        'grpc_ssl_server_name on;\n'\
        'grpc_ssl_name {0};\n'\
        'grpc_ssl_trusted_certificate /etc/{1}/client/all.pem;\n'\
        'grpc_ssl_certificate /etc/{1}/client/client.pem;\n'\
        'grpc_ssl_certificate_key /etc/{1}/client/client.key;'
    server_snippet = server_snippet_template.format(
        custom_host or '$http_x_host', name)
    client.create_or_update_ingress(
        metadata={
            'name': client_auth_ingress_name,
            'namespace': 'default',
            'annotations': {
                'kubernetes.io/ingress.class': 'nginx',
                'nginx.ingress.kubernetes.io/backend-protocol': 'GRPCS',
                'nginx.ingress.kubernetes.io/http2-insecure-port': 't',
                'nginx.ingress.kubernetes.io/configuration-snippet':
                configuration_snippet,
                'nginx.ingress.kubernetes.io/server-snippet': server_snippet
            }
        },
        spec={
            'rules': [{
                'host': client_auth_ingress_name,
                'http': {
                    'paths': [
                        {
                            'path': '/',
                            'backend': {
                                'serviceName': name,
                                'servicePort': port
                            }
                        }
                    ]
                }
            }]
        },
        name=client_auth_ingress_name
    )
