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
import datetime
import enum
import json
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Index
from fedlearner_webconsole.db import db, to_dict_mixin
from fedlearner_webconsole.k8s_client import get_client
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition

class JobState(enum.Enum):
    INVALID = 0
    STOPPED = 1
    WAITING = 2
    STARTED = 3


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


def merge(x, y):
    """Given two dictionaries, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z


@to_dict_mixin(
    extras={
        'state': (lambda job: job.get_state_for_frontend()),
        'pods': (lambda job: job.get_pods_for_frontend()),
        'config': (lambda job: job.get_config()),
        'complete_at': (lambda job: job.get_complete_at())
    })
class Job(db.Model):
    __tablename__ = 'job_v2'
    __table_args__ = (Index('idx_workflow_id', 'workflow_id'), {
        'comment': 'webconsole job',
        'mysql_engine': 'innodb',
        'mysql_charset': 'utf8mb4',
    })
    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   comment='id')
    name = db.Column(db.String(255), unique=True, comment='name')
    job_type = db.Column(db.Enum(JobType, native_enum=False),
                         nullable=False,
                         comment='job type')
    state = db.Column(db.Enum(JobState, native_enum=False),
                      nullable=False,
                      default=JobState.INVALID,
                      comment='state')
    config = db.Column(db.LargeBinary(16777215), comment='config')

    is_disabled = db.Column(db.Boolean(), default=False, comment='is_disabled')

    workflow_id = db.Column(db.Integer, nullable=False, comment='workflow id')
    project_id = db.Column(db.Integer, nullable=False, comment='project id')
    flapp_snapshot = db.Column(db.Text(16777215), comment='flapp snapshot')
    pods_snapshot = db.Column(db.Text(16777215), comment='pods snapshot')
    error_message = db.Column(db.Text(), comment='error message')

    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           comment='created at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           onupdate=func.now(),
                           comment='updated at')
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted at')

    project = db.relationship('Project',
                              primaryjoin='Project.id == '
                              'foreign(Job.project_id)')
    workflow = db.relationship('Workflow',
                               primaryjoin='Workflow.id == '
                               'foreign(Job.workflow_id)')
    _k8s_client = get_client()

    def get_config(self):
        if self.config is not None:
            proto = JobDefinition()
            proto.ParseFromString(self.config)
            return proto
        return None

    def set_config(self, proto):
        if proto is not None:
            self.config = proto.SerializeToString()
        else:
            self.config = None

    def _set_snapshot_flapp(self):
        def default(o):
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()
            return str(o)
        flapp = self._k8s_client.get_flapp(self.name)
        if flapp:
            self.flapp_snapshot = json.dumps(flapp, default=default)
        else:
            self.flapp_snapshot = None

    def get_flapp_details(self):
        if self.state == JobState.STARTED:
            flapp = self._k8s_client.get_flapp(self.name)
        elif self.flapp_snapshot is not None:
            flapp = json.loads(self.flapp_snapshot)
            # aims to support old job
            if 'flapp' not in flapp:
                flapp['flapp'] = None
            if 'pods' not in flapp and self.pods_snapshot:
                flapp['pods'] = json.loads(self.pods_snapshot)['pods']
        else:
            flapp = {'flapp': None, 'pods': {'items': []}}
        return flapp

    def get_pods_for_frontend(self, filter_private_info=False):
        result = []
        flapp_details = self.get_flapp_details()
        flapp = flapp_details['flapp']
        if flapp is None:
            return result
        if 'status' in flapp \
                and 'flReplicaStatus' in flapp['status']:
            replicas = flapp['status']['flReplicaStatus']
            if replicas:
                for pod_type in replicas:
                    for state in ['failed', 'succeeded']:
                        for pod in replicas[pod_type][state]:
                            result.append({
                                'name': pod,
                                'pod_type': pod_type,
                                'status': 'Flapp_{}'.format(state),
                                'message': '',
                            })

        # msg from pods
        pods = flapp_details['pods']['items']
        for pod in pods:
            status = pod['status']['phase'].lower()
            msgs = []
            # some fields may be None when pod get bootstrap
            if 'containerStatuses' in pod['status'] \
                    and pod['status']['containerStatuses']:
                state = pod['status']['containerStatuses'][0]['state']
                for key, detail in state.items():
                    if detail is None:
                        continue
                    if filter_private_info:
                        if 'reason' in detail and detail['reason']:
                            msgs.append(key + ':' + detail['reason'])
                    elif 'message' in detail and detail['message']:
                        msgs.append(key + ':' + detail['message'])

            if 'conditions' in pod['status'] and pod['status']['conditions']:
                for cond in pod['status']['conditions']:
                    if filter_private_info:
                        if 'reason' in cond and cond['reason']:
                            msgs.append(cond['type'] + ':' + cond['reason'])
                    elif 'message' in cond and cond['message']:
                        msgs.append(cond['type'] + ':' + cond['message'])

            result.append({
                'name': pod['metadata']['name'],
                'pod_type': pod['metadata']['labels']['fl-replica-type'],
                'status': status,
                'message': ', '.join(msgs)
            })

        # deduplication pods both in pods and flapp
        result = list({pod['name']: pod for pod in result}.values())
        return result

    def get_state_for_frontend(self):
        if self.state == JobState.STARTED:
            if self.is_complete():
                return 'COMPLETED'
            if self.is_failed():
                return 'FAILED'
            return 'RUNNING'
        if self.state == JobState.STOPPED:
            if self.get_flapp_details()['flapp'] is None:
                return 'NEW'
        return self.state.name

    def is_failed(self):
        flapp = self.get_flapp_details()['flapp']
        if flapp is None \
                or 'status' not in flapp \
                or 'appState' not in flapp['status']:
            return False
        return flapp['status']['appState'] in [
            'FLStateFailed', 'FLStateShutDown'
        ]

    def is_complete(self):
        flapp = self.get_flapp_details()['flapp']
        if flapp is None \
                or 'status' not in flapp \
                or 'appState' not in flapp['status']:
            return False
        return flapp['status']['appState'] == 'FLStateComplete'

    def get_complete_at(self):
        flapp = self.get_flapp_details()['flapp']
        if flapp is None \
                or 'status' not in flapp \
                or 'complete_at' not in flapp['status']:
            return None
        return flapp['status']['complete_at']

    def stop(self):
        if self.state == JobState.STARTED:
            self._set_snapshot_flapp()
            self._k8s_client.delete_flapp(self.name)
        self.state = JobState.STOPPED

    def schedule(self):
        assert self.state == JobState.STOPPED
        self.pods_snapshot = None
        self.flapp_snapshot = None
        self.state = JobState.WAITING

    def start(self):
        self.state = JobState.STARTED


class JobDependency(db.Model):
    __tablename__ = 'job_dependency_v2'
    __table_args__ = (Index('idx_src_job_id', 'src_job_id'),
                      Index('idx_dst_job_id', 'dst_job_id'), {
                          'comment': 'record job dependencies',
                          'mysql_engine': 'innodb',
                          'mysql_charset': 'utf8mb4',
                      })
    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   comment='id')
    src_job_id = db.Column(db.Integer, comment='src job id')
    dst_job_id = db.Column(db.Integer, comment='dst job id')
    dep_index = db.Column(db.Integer, comment='dep index')
