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
from typing import Callable, Any, Optional, Tuple

import grpc

from fedlearner_webconsole.db import db
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.rpc.auth import get_common_name, SSL_CLIENT_SUBJECT_DN_HEADER, PROJECT_NAME_HEADER
from fedlearner_webconsole.rpc.v2.utils import decode_project_name
from fedlearner_webconsole.utils.domain_name import get_pure_domain_name

# Which services should disable the auth interceptors.
DISABLED_SERVICES = frozenset([
    # Skips the old gRPC service as it has a separate way to check auth.
    'fedlearner_webconsole.proto.WebConsoleV2Service',
])
# Which services should use project-based auth interceptors.
PROJECT_BASED_SERVICES = frozenset([
    'fedlearner_webconsole.proto.rpc.v2.JobService',
])


class AuthException(Exception):

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _get_handler_factory(handler: grpc.RpcMethodHandler) -> Callable:
    if handler.unary_unary:
        return grpc.unary_unary_rpc_method_handler
    if handler.unary_stream:
        return grpc.unary_stream_rpc_method_handler
    if handler.stream_unary:
        return grpc.stream_unary_rpc_method_handler
    if handler.stream_stream:
        return grpc.stream_stream_rpc_method_handler
    raise RuntimeError(f'Unrecognized rpc handler: {handler}')


def _parse_method_name(method_full_name: str) -> Tuple[str, str]:
    """Parses grpc method name in service interceptor.

    Arguments:
        method_full_name: Full name of the method, e.g. /fedlearner_webconsole.proto.testing.TestService/FakeUnaryUnary

    Returns:
        A tuple of service name and method name, e.g. 'fedlearner_webconsole.proto.testing.TestService'
    and 'FakeUnaryUnary'.
    """
    names = method_full_name.split('/')
    return names[-2], names[-1]


class AuthServerInterceptor(grpc.ServerInterceptor):
    """Auth related stuff on server side, which will work for those service which injects this
    interceptor.

    Ref: https://github.com/grpc/grpc/blob/v1.40.x/examples/python/interceptors/headers/request_header_validator_interceptor.py  # pylint:disable=line-too-long
    """

    def _build_rpc_terminator(self, message: str):

        def terminate(request_or_iterator: Any, context: grpc.ServicerContext):
            context.abort(grpc.StatusCode.UNAUTHENTICATED, message)

        return terminate

    def _verify_domain_name(self, handler_call_details: grpc.HandlerCallDetails) -> str:
        """Verifies if the traffic is secure by checking ssl-client-subject-dn header.

        Returns:
            The pure domain name.

        Raises:
            AuthException: if the traffic is insecure.
        """
        ssl_client_subject_dn = None
        for header, value in handler_call_details.invocation_metadata:
            if header == SSL_CLIENT_SUBJECT_DN_HEADER:
                ssl_client_subject_dn = value
                break
        if not ssl_client_subject_dn:
            raise AuthException('No client subject dn found')
        # If this header is set, it passed the TLS verification
        common_name = get_common_name(ssl_client_subject_dn)
        if not common_name:
            logging.error('[gRPC auth] invalid subject dn: %s', ssl_client_subject_dn)
            raise AuthException('Invalid subject dn')
        # Extracts the pure domain name, e.g. bytedance-test
        pure_domain_name = get_pure_domain_name(common_name)
        if not pure_domain_name:
            logging.error('[gRPC auth] no valid domain name found in %s', ssl_client_subject_dn)
            raise AuthException('Invalid domain name')
        return pure_domain_name

    def _verify_project_info(self, handler_call_details: grpc.HandlerCallDetails, pure_domain_name: str):
        project_name = None
        for header, value in handler_call_details.invocation_metadata:
            if header == PROJECT_NAME_HEADER:
                project_name = decode_project_name(value)
                break
        if not project_name:
            raise AuthException('No project name found')
        with db.session_scope() as session:
            project = session.query(Project.id).filter_by(name=project_name).first()
            if not project:
                logging.error('[gRPC auth] invalid project: %s', project_name)
                raise AuthException(f'Invalid project {project_name}')
            project_id, = project
            # Checks if the caller has the access to this project
            service = ParticipantService(session)
            participants = service.get_participants_by_project(project_id)
            has_access = False
            for p in participants:
                if p.pure_domain_name() == pure_domain_name:
                    has_access = True
                    break
            if not has_access:
                raise AuthException(f'No access to {project_name}')

    def intercept_service(self, continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler],
                          handler_call_details: grpc.HandlerCallDetails) -> Optional[grpc.RpcMethodHandler]:
        next_handler = continuation(handler_call_details)

        package_service_name, _ = _parse_method_name(handler_call_details.method)
        # Skips the interceptor if the service does not intend to use it
        if package_service_name in DISABLED_SERVICES:
            return next_handler

        try:
            pure_domain_name = self._verify_domain_name(handler_call_details)
            # Project based service
            if package_service_name in PROJECT_BASED_SERVICES:
                self._verify_project_info(handler_call_details, pure_domain_name)
            # Go ahead!
            return next_handler
        except AuthException as e:
            handler_factory = _get_handler_factory(next_handler)
            return handler_factory(self._build_rpc_terminator(e.message))
