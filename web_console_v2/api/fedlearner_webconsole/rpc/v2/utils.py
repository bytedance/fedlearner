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

from grpc import ServicerContext
from typing import Tuple
from sqlalchemy.orm import Session
from fedlearner_webconsole.rpc.auth import get_common_name, SSL_CLIENT_SUBJECT_DN_HEADER, PROJECT_NAME_HEADER
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.utils.domain_name import get_pure_domain_name
from fedlearner_webconsole.utils.pp_base64 import base64decode, base64encode


def get_grpc_context_info(session: Session, context: ServicerContext) -> Tuple[int, int]:
    metadata = dict(context.invocation_metadata())
    project_name = decode_project_name(metadata.get(PROJECT_NAME_HEADER))
    project_id, *_ = session.query(Project.id).filter_by(name=project_name).first()
    cn = get_common_name(metadata.get(SSL_CLIENT_SUBJECT_DN_HEADER))
    client_id = ParticipantService(session).get_participant_by_pure_domain_name(get_pure_domain_name(cn)).id
    return project_id, client_id


def get_pure_domain_from_context(context: ServicerContext) -> str:
    metadata = dict(context.invocation_metadata())
    cn = get_common_name(metadata.get(SSL_CLIENT_SUBJECT_DN_HEADER))
    return get_pure_domain_name(cn)


def _is_ascii(s: str) -> bool:
    return all(ord(c) < 128 for c in s)


def encode_project_name(project_name: str) -> str:
    """Encodes project name to grpc-acceptable format.

    gRPC does not recognize unicode in headers, and due to historical
    reason, we have to be compatiable with anscii strings, otherwise
    old gRPC server can not get the project name correctly."""
    if _is_ascii(project_name):
        return project_name
    return base64encode(project_name)


def decode_project_name(encoded: str) -> str:
    try:
        return base64decode(encoded)
    except Exception:  # pylint: disable=broad-except
        # Not a base64 encoded string
        pass
    # Encoded as raw, see details in `encode_project_name`
    return encoded
