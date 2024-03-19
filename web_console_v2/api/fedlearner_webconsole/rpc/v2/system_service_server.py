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

from fedlearner_webconsole.db import db
from fedlearner_webconsole.flag.models import get_flags
from fedlearner_webconsole.proto.rpc.v2 import system_service_pb2_grpc
from fedlearner_webconsole.proto.rpc.v2.system_service_pb2 import (CheckHealthResponse, CheckHealthRequest,
                                                                   ListFlagsRequest, ListFlagsResponse,
                                                                   CheckTeeEnabledRequest, CheckTeeEnabledResponse)
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.tee.services import check_tee_enabled


# TODO(linfan.fine): adds request id decorator
class SystemGrpcService(system_service_pb2_grpc.SystemServiceServicer):

    def CheckHealth(self, request: CheckHealthRequest, context: ServicerContext):
        with db.session_scope() as session:
            version = SettingService(session).get_application_version()
        return CheckHealthResponse(application_version=version.to_proto(), healthy=True)

    def ListFlags(self, request: ListFlagsRequest, context: ServicerContext):
        resp = ListFlagsResponse()
        resp.flags.update(get_flags())
        return resp

    def CheckTeeEnabled(self, request: CheckTeeEnabledRequest, context: ServicerContext):
        return CheckTeeEnabledResponse(tee_enabled=check_tee_enabled())
