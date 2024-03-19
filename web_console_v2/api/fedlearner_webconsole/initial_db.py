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
import collections
import json
import os

from pathlib import Path

from sqlalchemy.orm import Session
from google.protobuf.json_format import ParseDict

from fedlearner_webconsole.auth.models import Role, State, User
from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput
from fedlearner_webconsole.proto.setting_pb2 import SystemVariables
from fedlearner_webconsole.setting.models import Setting
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate, WorkflowTemplateKind
from fedlearner_webconsole.proto.workflow_definition_pb2 import (WorkflowDefinition, WorkflowTemplateEditorInfo)
from fedlearner_webconsole.composer.composer_service import ComposerService
from fedlearner_webconsole.flag.models import Flag

SettingTuple = collections.namedtuple('SettingTuple', ['key', 'value'])

INITIAL_USER_INFO = [{
    'username': 'ada',
    'password': 'fl@12345.',
    'name': 'ada',
    'email': 'ada@fedlearner.com',
    'role': Role.USER,
    'state': State.ACTIVE,
}, {
    'username': 'admin',
    'password': 'fl@12345.',
    'name': 'admin',
    'email': 'admin@fedlearner.com',
    'role': Role.ADMIN,
    'state': State.ACTIVE,
}, {
    'username': 'robot',
    'password': 'fl@12345.',
    'name': 'robot',
    'email': 'robot@fedlearner.com',
    'role': Role.ADMIN,
    'state': State.ACTIVE,
}]

INITIAL_SYSTEM_VARIABLES = ParseDict(
    {
        'variables': [{
            'name': 'labels',
            'value': {},
            'value_type': 'OBJECT',
            'fixed': True
        }, {
            'name': 'volume_mounts_list',
            'value': [{
                'mountPath': '/data',
                'name': 'data'
            }],
            'value_type': 'LIST',
            'fixed': True
        }, {
            'name': 'volumes_list',
            'value': [{
                'persistentVolumeClaim': {
                    'claimName': 'pvc-fedlearner-default'
                },
                'name': 'data'
            }],
            'value_type': 'LIST',
            'fixed': True
        }, {
            'name': 'envs_list',
            'value': [{
                'name': 'HADOOP_HOME',
                'value': ''
            }, {
                'name': 'MANUFACTURER',
                'value': 'dm9sY2VuZ2luZQ=='
            }],
            'value_type': 'LIST',
            'fixed': True
        }, {
            'name': 'namespace',
            'value': 'default',
            'value_type': 'STRING',
            'fixed': True
        }, {
            'name': 'serving_image',
            'value': 'artifact.bytedance.com/fedlearner/'
                     'privacy_perserving_computing_serving:7359b10685e1646450dfda389d228066',
            'value_type': 'STRING',
            'fixed': True
        }, {
            'name': 'spark_image',
            'value': 'artifact.bytedance.com/fedlearner/pp_data_inspection:2.2.4.1',
            'value_type': 'STRING',
            'fixed': True
        }, {
            'name': 'image_repo',
            'value': 'artifact.bytedance.com/fedlearner',
            'value_type': 'STRING',
            'fixed': False
        }]
    }, SystemVariables())

INITIAL_EMAIL_GROUP = SettingTuple(key='sys_email_group', value='privacy_computing@bytedance.com')


def _insert_setting_if_not_exists(session: Session, st: SettingTuple):
    if session.query(Setting).filter_by(uniq_key=st.key).first() is None:
        setting = Setting(uniq_key=st.key, value=st.value)
        session.add(setting)


def migrate_system_variables(session: Session, initial_vars: SystemVariables):
    setting_service = SettingService(session)
    origin_sys_vars = setting_service.get_system_variables()
    result = merge_system_variables(initial_vars, origin_sys_vars)
    setting_service.set_system_variables(result)


def merge_system_variables(extend: SystemVariables, origin: SystemVariables) -> SystemVariables:
    """Merge two Systemvariables, when two SystemVariable has the same name, use origin's value."""
    key_map = {var.name: var for var in extend.variables}
    for var in origin.variables:
        key_map[var.name] = var
    return SystemVariables(variables=[key_map[key] for key in key_map])


def _insert_or_update_templates(session: Session):
    path = Path(__file__, '../sys_preset_templates/').resolve()
    template_files = path.rglob('*.json')
    for template_file in template_files:
        with open(os.path.join(path, template_file), encoding='utf-8') as f:
            data = json.load(f)
            template_proto = ParseDict(data['config'], WorkflowDefinition(), ignore_unknown_fields=True)
            editor_info_proto = ParseDict(data['editor_info'], WorkflowTemplateEditorInfo(), ignore_unknown_fields=True)
            template = session.query(WorkflowTemplate).filter_by(name=data['name']).first()
            if template is None:
                template = WorkflowTemplate(name=data['name'])
            template.comment = data['comment']
            template.group_alias = template_proto.group_alias
            template.kind = WorkflowTemplateKind.PRESET.value
            template.set_config(template_proto)
            template.set_editor_info(editor_info_proto)
            session.add(template)


def _insert_schedule_workflow_item(session):
    composer_service = ComposerService(session)
    # Finishes the old one
    composer_service.finish('workflow_scheduler')
    composer_service.collect_v2(
        'workflow_scheduler_v2',
        items=[(ItemType.SCHEDULE_WORKFLOW, RunnerInput())],
        # cron job at every 1 minute, specific time to avoid congestion.
        cron_config='* * * * * 45')
    composer_service.collect_v2(
        'job_scheduler_v2',
        items=[(ItemType.SCHEDULE_JOB, RunnerInput())],
        # cron job at every 1 minute, specific time to avoid congestion.
        cron_config='* * * * * 15')


def _insert_dataset_job_scheduler_item(session):
    composer_service = ComposerService(session)
    # finish the old scheduler
    composer_service.finish('dataset_job_scheduler')
    composer_service.finish('dataset_cron_job_scheduler')
    # insert new scheduler
    composer_service.collect_v2(
        'dataset_short_period_scheduler',
        items=[(ItemType.DATASET_SHORT_PERIOD_SCHEDULER, RunnerInput())],
        # cron job at every 30 seconds
        cron_config='* * * * * */30')
    composer_service.collect_v2(
        'dataset_long_period_scheduler',
        items=[(ItemType.DATASET_LONG_PERIOD_SCHEDULER, RunnerInput())],
        # cron job at every 30 min
        cron_config='*/30 * * * *')


def _insert_cleanup_cronjob_item(session):
    composer_service = ComposerService(session)
    composer_service.collect_v2(
        'cleanup_cron_job',
        items=[(ItemType.CLEANUP_CRON_JOB, RunnerInput())],
        # cron job at every 30 min
        cron_config='*/30 * * * *')


def _insert_tee_runner_item(session):
    if not Flag.TRUSTED_COMPUTING_ENABLED.value:
        return
    composer_service = ComposerService(session)
    composer_service.collect_v2(
        'tee_create_runner',
        items=[(ItemType.TEE_CREATE_RUNNER, RunnerInput())],
        # cron job at every 30 seconds
        cron_config='* * * * * */30')
    composer_service.collect_v2(
        'tee_resource_check_runner',
        items=[(ItemType.TEE_RESOURCE_CHECK_RUNNER, RunnerInput())],
        # cron job at every 30 min
        cron_config='*/30 * * * *')


def _insert_project_runner_item(session):
    if not Flag.PENDING_PROJECT_ENABLED.value:
        return
    composer_service = ComposerService(session)
    composer_service.collect_v2(
        'project_scheduler_v2',
        items=[(ItemType.SCHEDULE_PROJECT, RunnerInput())],
        # cron job at every 1 minute, specific time to avoid congestion.
        cron_config='* * * * * 30')


def _insert_model_job_scheduler_runner_item(session: Session):
    if not Flag.MODEL_JOB_GLOBAL_CONFIG_ENABLED:
        return
    composer_service = ComposerService(session)
    composer_service.collect_v2('model_job_scheduler_runner',
                                items=[(ItemType.SCHEDULE_MODEL_JOB, RunnerInput())],
                                cron_config='* * * * * */30')


def _insert_model_job_group_scheduler_runner_item(session: Session):
    if not Flag.MODEL_JOB_GLOBAL_CONFIG_ENABLED:
        return
    composer_service = ComposerService(session)
    composer_service.collect_v2('model_job_group_scheduler_runner',
                                items=[(ItemType.SCHEDULE_MODEL_JOB_GROUP, RunnerInput())],
                                cron_config='* * * * * */30')
    composer_service.collect_v2(
        'model_job_group_long_period_scheduler_runner',
        items=[(ItemType.SCHEDULE_LONG_PERIOD_MODEL_JOB_GROUP, RunnerInput())],
        # cron job at every 30 min
        cron_config='*/30 * * * *')


def initial_db():
    with db.session_scope() as session:
        # Initializes user info first
        for u_info in INITIAL_USER_INFO:
            username = u_info['username']
            password = u_info['password']
            name = u_info['name']
            email = u_info['email']
            role = u_info['role']
            state = u_info['state']
            if session.query(User).filter_by(username=username).first() is None:
                user = User(username=username, name=name, email=email, role=role, state=state)
                user.set_password(password=password)
                session.add(user)
        # Initializes settings
        _insert_setting_if_not_exists(session, INITIAL_EMAIL_GROUP)
        migrate_system_variables(session, INITIAL_SYSTEM_VARIABLES)
        _insert_or_update_templates(session)
        _insert_schedule_workflow_item(session)
        _insert_dataset_job_scheduler_item(session)
        _insert_cleanup_cronjob_item(session)
        _insert_tee_runner_item(session)
        _insert_project_runner_item(session)
        _insert_model_job_scheduler_runner_item(session)
        _insert_model_job_group_scheduler_runner_item(session)
        session.commit()
