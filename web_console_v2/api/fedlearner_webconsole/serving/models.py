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

import enum
import json

from sqlalchemy.sql.schema import UniqueConstraint, Index

from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.proto import serving_pb2
from fedlearner_webconsole.utils.pp_datetime import now, to_timestamp
from fedlearner_webconsole.mmgr.models import ModelType


class ServingModelStatus(enum.Enum):
    UNKNOWN = 0
    LOADING = 1
    AVAILABLE = 2
    UNLOADING = 3
    PENDING_ACCEPT = 4
    DELETED = 5
    WAITING_CONFIG = 6


class ServingDeploymentStatus(enum.Enum):
    UNAVAILABLE = 0
    AVAILABLE = 1


class ServingModel(db.Model):
    __tablename__ = 'serving_models_v2'
    __table_args__ = (UniqueConstraint('name', name='uniq_name'), default_table_args('serving models'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id')
    project_id = db.Column(db.Integer, nullable=False, comment='project id')
    name = db.Column(db.String(255), comment='name')
    serving_deployment_id = db.Column(db.Integer, comment='serving deployment db id')
    comment = db.Column('cmt', db.Text(), key='comment', comment='comment')
    model_id = db.Column(db.Integer, comment='model id')
    model_type = db.Column(db.Enum(ModelType, native_enum=False, length=64, create_constraint=False),
                           default=ModelType.NN_MODEL,
                           comment='model type')
    model_path = db.Column(db.String(255), default=None, comment='model\'s path')
    model_group_id = db.Column(db.Integer, comment='model group id for auto update scenario')
    pending_model_id = db.Column(db.Integer, comment='model id when waiting for participants\' config')
    pending_model_group_id = db.Column(db.Integer, comment='model group id when waiting for participants\' config')
    signature = db.Column(db.Text(), default='', comment='model signature')
    status = db.Column(db.Enum(ServingModelStatus, native_enum=False, length=64, create_constraint=False),
                       default=ServingModelStatus.UNKNOWN,
                       comment='status')
    endpoint = db.Column(db.String(255), comment='endpoint')
    created_at = db.Column(db.DateTime(timezone=True), comment='created_at', default=now)
    updated_at = db.Column(db.DateTime(timezone=True), comment='updated_at', default=now, onupdate=now)
    extra = db.Column(db.Text(), comment='extra')

    project = db.relationship('Project', primaryjoin='Project.id == foreign(ServingModel.project_id)')
    serving_deployment = db.relationship('ServingDeployment',
                                         primaryjoin='ServingDeployment.id == '
                                         'foreign(ServingModel.serving_deployment_id)')
    model = db.relationship('Model', primaryjoin='Model.id == foreign(ServingModel.model_id)')
    pending_model = db.relationship('Model', primaryjoin='Model.id == foreign(ServingModel.pending_model_id)')
    model_group = db.relationship('ModelJobGroup',
                                  primaryjoin='ModelJobGroup.id == foreign(ServingModel.model_group_id)')
    pending_model_group = db.relationship('ModelJobGroup',
                                          primaryjoin='ModelJobGroup.id == '
                                          'foreign(ServingModel.pending_model_group_id)')

    def to_serving_service(self) -> serving_pb2.ServingService:
        return serving_pb2.ServingService(id=self.id,
                                          project_id=self.project_id,
                                          name=self.name,
                                          comment=self.comment,
                                          is_local=True,
                                          status=self.status.name,
                                          support_inference=False,
                                          created_at=to_timestamp(self.created_at),
                                          updated_at=to_timestamp(self.updated_at))

    def to_serving_service_detail(self) -> serving_pb2.ServingServiceDetail:
        detail = serving_pb2.ServingServiceDetail(id=self.id,
                                                  project_id=self.project_id,
                                                  name=self.name,
                                                  comment=self.comment,
                                                  model_id=self.model_id,
                                                  model_group_id=self.model_group_id,
                                                  model_type=self.model_type.name,
                                                  is_local=True,
                                                  endpoint=self.endpoint,
                                                  signature=self.signature,
                                                  status=self.status.name,
                                                  support_inference=False,
                                                  created_at=to_timestamp(self.created_at),
                                                  updated_at=to_timestamp(self.updated_at))
        if self.serving_deployment.is_remote_serving():
            platform_config: dict = json.loads(self.serving_deployment.deploy_platform)
            detail.remote_platform.CopyFrom(
                serving_pb2.ServingServiceRemotePlatform(
                    platform=platform_config['platform'],
                    payload=platform_config['payload'],
                ))
        return detail


class ServingDeployment(db.Model):
    __tablename__ = 'serving_deployments_v2'
    __table_args__ = (default_table_args('serving deployments in webconsole'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id')
    project_id = db.Column(db.Integer, nullable=False, comment='project id')
    deployment_name = db.Column(db.String(255), comment='deployment name')
    resource = db.Column('rsc', db.String(255), comment='resource')
    endpoint = db.Column(db.String(255), comment='endpoint')
    deploy_platform = db.Column(db.Text(), comment='deploy platform. None means inside this platform')
    status = db.Column(db.Enum(ServingDeploymentStatus, native_enum=False, length=64, create_constraint=False),
                       default=ServingDeploymentStatus.UNAVAILABLE,
                       comment='status')
    created_at = db.Column(db.DateTime(timezone=True), comment='created_at', default=now)
    extra = db.Column(db.Text(), comment='extra')

    project = db.relationship('Project', primaryjoin='Project.id == foreign(ServingDeployment.project_id)')

    def is_remote_serving(self) -> bool:
        return self.deploy_platform is not None


class ServingNegotiator(db.Model):
    __tablename__ = 'serving_negotiators_v2'
    __table_args__ = (Index('idx_serving_model_uuid',
                            'serving_model_uuid'), default_table_args('serving negotiators in webconsole'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id')
    project_id = db.Column(db.Integer, nullable=False, comment='project id')
    serving_model_id = db.Column(db.Integer, nullable=False, comment='serving model id')
    is_local = db.Column(db.Boolean, comment='can serving locally')
    with_label = db.Column(db.Boolean, comment='federal side with label or not')
    serving_model_uuid = db.Column(db.String(255), comment='uuid for federal model')
    feature_dataset_id = db.Column(db.Integer, comment='feature dataset id')
    data_source_map = db.Column(db.Text(), comment='where to get model inference arguments')
    raw_signature = db.Column(db.Text(), comment='save raw signature from tf serving')
    created_at = db.Column(db.DateTime(timezone=True), comment='created_at', default=now)
    extra = db.Column(db.Text(), comment='extra')

    project = db.relationship('Project', primaryjoin='Project.id == foreign(ServingNegotiator.project_id)')
    serving_model = db.relationship('ServingModel',
                                    primaryjoin='ServingModel.id == '
                                    'foreign(ServingNegotiator.serving_model_id)')
