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

import logging
from pathlib import Path

from deploy.auto_cert.certificate_model_pb2 import CertificateFile
from deploy.auto_cert.certificate_service import CertificateService
from deploy.auto_cert.authenticator import ApiKeyAuthenticator
from deploy.auto_cert.consts import BOE_NEXUS_CONFIG


def get_certificate(company_name: str, authenticator: ApiKeyAuthenticator) -> CertificateFile:
    service = CertificateService(authenticator, BOE_NEXUS_CONFIG)
    common_name = f'{company_name}.fedlearner.net'
    certs = service.get_certificates_by_name(common_name)
    if len(certs) == 0:
        logging.info(f'Certificate with company_name={company_name} not found; issuing...')
        cert = service.issue_certificate(common_name, 365)
    else:
        cert = list(certs.values())[0]
    return cert


def write_certificate(cert_path: Path, cert: CertificateFile):
    with open(cert_path / 'public.pem', mode='w', encoding='utf-8') as f:
        f.write(cert.certificate)
    with open(cert_path / 'intermediate.pem', mode='w', encoding='utf-8') as f:
        f.write('\n'.join(cert.certificate_chain))
    with open(cert_path / 'private.key', mode='w', encoding='utf-8') as f:
        f.write(cert.private_key)
