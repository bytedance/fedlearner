# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import enum
import json

from typing import Optional

from google.protobuf import text_format
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Index
from fedlearner_webconsole.job.crd import CrdService
from fedlearner_webconsole.k8s.models import K8sApp, PodState
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.mixins import to_dict_mixin
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition
from fedlearner_webconsole.proto.job_pb2 import CrdMetaData, JobPb, JobErrorMessage


class JobState(enum.Enum):
    # VALID TRANSITION:
    # 1. NEW : init by workflow
    # 2. NEW/STOPPED/COMPLTED/FAILED -> WAITING: triggered by user, run workflow
    # 3. WAITING -> STARTED: triggered by scheduler
    # 4. WAITING -> NEW: triggered by user, stop workflow
    # 4. STARTED -> STOPPED: triggered by user, stop workflow
    # 5. STARTED -> COMPLETED/FAILED: triggered by k8s_watcher
    INVALID = 0  # INVALID STATE
    STOPPED = 1  # STOPPED BY USER
    WAITING = 2  # SCHEDULED, WAITING FOR RUNNING
    STARTED = 3  # RUNNING
    NEW = 4  # BEFORE SCHEDULE
    COMPLETED = 5  # SUCCEEDED JOB
    FAILED = 6  # FAILED JOB


# must be consistent with JobType in proto
class JobType(enum.Enum):
    UNSPECIFIED = 0
    RAW_DATA = 1
    DATA_JOIN = 2
    PSI_DATA_JOIN = 3
    NN_MODEL_TRANINING = 4
    TREE_MODEL_TRAINING = 5
    NN_MODEL_EVALUATION = 6
    TREE_MODEL_EVALUATION = 7
    TRANSFORMER = 8
    ANALYZER = 9
    CUSTOMIZED = 10


@to_dict_mixin(ignores=['config'], extras={'complete_at': (lambda job: job.get_complete_at())})
class Job(db.Model):
    __tablename__ = 'job_v2'
    __table_args__ = (Index('idx_workflow_id', 'workflow_id'), {
        'comment': 'webconsole job',
        'mysql_engine': 'innodb',
        'mysql_charset': 'utf8mb4',
    })
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id')
    name = db.Column(db.String(255), unique=True, comment='name')
    job_type = db.Column(db.Enum(JobType, native_enum=False, create_constraint=False),
                         nullable=False,
                         comment='job type')
    state = db.Column(db.Enum(JobState, native_enum=False, create_constraint=False),
                      nullable=False,
                      default=JobState.INVALID,
                      comment='state')
    config = db.Column(db.LargeBinary(16777215), comment='config')

    is_disabled = db.Column(db.Boolean(), default=False, comment='is_disabled')

    workflow_id = db.Column(db.Integer, nullable=False, comment='workflow id')
    project_id = db.Column(db.Integer, nullable=False, comment='project id')
    flapp_snapshot = db.Column(db.Text(16777215), comment='flapp snapshot')  # deprecated
    sparkapp_snapshot = db.Column(db.Text(16777215), comment='sparkapp snapshot')  # deprecated
    # Format like {'app': app_status_dict, 'pods': {'items': pod_list}}.
    snapshot = db.Column(db.Text(16777215), comment='snapshot')
    error_message = db.Column(db.Text(), comment='error message')
    crd_meta = db.Column(db.Text(), comment='metadata')
    # Use string but not enum, in order to support all kinds of crd to create and delete,
    # but only FLApp SparkApplication and FedApp support getting pods and auto finish.
    crd_kind = db.Column(db.String(255), comment='kind')

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           onupdate=func.now(),
                           comment='updated at')
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted at')

    project = db.relationship(Project.__name__, primaryjoin='Project.id == ' 'foreign(Job.project_id)')
    workflow = db.relationship('Workflow', primaryjoin='Workflow.id == ' 'foreign(Job.workflow_id)')

    def get_config(self) -> Optional[JobDefinition]:
        if self.config is not None:
            proto = JobDefinition()
            proto.ParseFromString(self.config)
            return proto
        return None

    def set_config(self, proto: JobDefinition):
        if proto is not None:
            self.config = proto.SerializeToString()
        else:
            self.config = None

    # TODO(xiangyuxuan.prs): Remove this func and get_completed_at from model to service.
    def get_k8s_app(self) -> K8sApp:
        snapshot = None
        if self.state != JobState.STARTED:
            snapshot = self.snapshot or '{}'
            snapshot = json.loads(snapshot)
        return self.build_crd_service().get_k8s_app(snapshot)

    def build_crd_service(self) -> CrdService:
        if self.crd_kind is not None:
            return CrdService(self.crd_kind, self.get_crd_meta().api_version, self.name)
        # TODO(xiangyuxuan.prs): Adapt to old data, remove in the future.
        if self.job_type in [JobType.TRANSFORMER]:
            return CrdService('SparkApplication', 'sparkoperator.k8s.io/v1beta2', self.name)
        return CrdService('FLApp', 'fedlearner.k8s.io/v1alpha1', self.name)

    def is_training_job(self):
        return self.job_type in [JobType.NN_MODEL_TRANINING, JobType.TREE_MODEL_TRAINING]

    def get_complete_at(self) -> Optional[int]:
        crd_obj = self.get_k8s_app()
        return crd_obj.completed_at

    def get_start_at(self) -> int:
        crd_obj = self.get_k8s_app()
        return crd_obj.creation_timestamp

    def get_crd_meta(self) -> CrdMetaData:
        crd_meta_obj = CrdMetaData()
        if self.crd_meta is not None:
            return text_format.Parse(self.crd_meta, crd_meta_obj)
        return crd_meta_obj

    def set_crd_meta(self, crd_meta: Optional[CrdMetaData] = None):
        if crd_meta is None:
            crd_meta = CrdMetaData()
        self.crd_meta = text_format.MessageToString(crd_meta)

    def get_error_message_with_pods(self) -> JobErrorMessage:
        failed_pods_msg = {}
        for pod in self.get_k8s_app().pods:
            if pod.state != PodState.FAILED:
                continue
            pod_error_msg = pod.get_message(include_private_info=True).summary
            if pod_error_msg:
                failed_pods_msg[pod.name] = pod_error_msg
        return JobErrorMessage(app=self.error_message, pods=failed_pods_msg)

    def to_proto(self) -> JobPb:
        return JobPb(id=self.id,
                     name=self.name,
                     job_type=self.job_type.value,
                     state=self.state.name,
                     is_disabled=self.is_disabled,
                     workflow_id=self.workflow_id,
                     project_id=self.project_id,
                     snapshot=self.snapshot,
                     error_message=self.get_error_message_with_pods(),
                     crd_meta=self.get_crd_meta(),
                     crd_kind=self.crd_kind,
                     created_at=to_timestamp(self.created_at),
                     updated_at=to_timestamp(self.updated_at),
                     complete_at=self.get_complete_at(),
                     start_at=self.get_start_at())


class JobDependency(db.Model):
    __tablename__ = 'job_dependency_v2'
    __table_args__ = (Index('idx_src_job_id', 'src_job_id'), Index('idx_dst_job_id', 'dst_job_id'), {
        'comment': 'record job dependencies',
        'mysql_engine': 'innodb',
        'mysql_charset': 'utf8mb4',
    })
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id')
    src_job_id = db.Column(db.Integer, comment='src job id')
    dst_job_id = db.Column(db.Integer, comment='dst job id')
    dep_index = db.Column(db.Integer, comment='dep index')
