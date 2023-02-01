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
from typing import Tuple

from envs import Envs
from fedlearner_webconsole.db import db
from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.interface import IRunnerV2
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.proto.composer_pb2 import RunnerOutput, TeeRunnerOutput
from fedlearner_webconsole.proto import dataset_pb2
from fedlearner_webconsole.tee.models import TrustedJobGroup, GroupCreateStatus, TrustedJob, TrustedJobType, \
    TrustedJobStatus
from fedlearner_webconsole.tee.utils import get_pure_path
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.tee.controller import create_trusted_job_group, TrustedJobGroupController, \
    launch_trusted_job, TrustedJobController, launch_trusted_export_job
from fedlearner_webconsole.exceptions import WebConsoleApiException
from fedlearner_webconsole.dataset.services import DatasetService, BatchService
from fedlearner_webconsole.dataset.models import DatasetType, DatasetKindV2, DatasetFormat, ImportType, StoreFormat


class TeeCreateRunner(IRunnerV2):

    @staticmethod
    def _create_trusted_job_group():
        # schedule all groups with ticket APPROVED, status PENDING and coordinator_id 0
        processed_groups = set()
        with db.session_scope() as session:
            groups_ids = session.query(TrustedJobGroup.id).filter_by(ticket_status=TicketStatus.APPROVED,
                                                                     status=GroupCreateStatus.PENDING,
                                                                     coordinator_id=0).all()
        for group_id, *_ in groups_ids:
            with db.session_scope() as session:
                group: TrustedJobGroup = session.query(TrustedJobGroup).populate_existing().with_for_update().get(
                    group_id)
                if group.status != GroupCreateStatus.PENDING:
                    continue
                processed_groups.add(group.id)
                try:
                    succeeded, msg = create_trusted_job_group(group)
                except WebConsoleApiException as e:
                    succeeded = False
                    msg = e.details
                if not succeeded:
                    group.status = GroupCreateStatus.FAILED
                    logging.warning(f'[create trusted job group scheduler]: group {group.id} failed, exception {msg}')
                else:
                    group.status = GroupCreateStatus.SUCCEEDED
                session.commit()
        return processed_groups

    @staticmethod
    def _launch_trusted_job():
        # schedule all newly created trusted job group satisfy
        # state == SUCCEEDED and coordinator_id == 0 and version == 0 and
        # auth_status == AUTHORIZED and unauth_participant_ids == None
        processed_groups = set()
        with db.session_scope() as session:
            groups_ids = session.query(TrustedJobGroup.id).filter_by(status=GroupCreateStatus.SUCCEEDED,
                                                                     coordinator_id=0,
                                                                     latest_version=0,
                                                                     unauth_participant_ids=None,
                                                                     auth_status=AuthStatus.AUTHORIZED)
        for group_id, *_ in groups_ids:
            with db.session_scope() as session:
                group: TrustedJobGroup = session.query(TrustedJobGroup).populate_existing().with_for_update().get(
                    group_id)
                if group.latest_version or group.auth_status != AuthStatus.AUTHORIZED or group.unauth_participant_ids:
                    continue
                group.latest_version = 1
                session.commit()
            processed_groups.add(group.id)
            succeeded, msg = launch_trusted_job(group.project_id, group.uuid, group.latest_version)
            if not succeeded:
                logging.warning(f'[launch trusted job scheduler]: group {group.id} failed, exception {msg}')
        return processed_groups

    @staticmethod
    def _create_trusted_export_job():
        processed_ids = set()
        with db.session_scope() as session:
            trusted_jobs_ids = session.query(TrustedJob.id).filter_by(
                type=TrustedJobType.EXPORT,
                ticket_status=TicketStatus.APPROVED,
                status=TrustedJobStatus.NEW,
            ).all()
        for trusted_job_id, *_ in trusted_jobs_ids:
            with db.session_scope() as session:
                tee_export_job = session.query(TrustedJob).populate_existing().with_for_update().get(trusted_job_id)
                tee_analyze_job = session.query(TrustedJob).filter_by(
                    type=TrustedJobType.ANALYZE,
                    trusted_job_group_id=tee_export_job.trusted_job_group_id,
                    version=tee_export_job.version).first()
                processed_ids.add(tee_export_job.id)
                try:
                    TrustedJobController(session, tee_export_job.project_id).create_trusted_export_job(
                        tee_export_job, tee_analyze_job)
                    tee_export_job.status = TrustedJobStatus.CREATED
                except WebConsoleApiException as e:
                    tee_export_job.status = TrustedJobStatus.CREATE_FAILED
                    logging.warning(
                        f'[create trusted export job scheduler]: {tee_export_job.id} failed, exception {e.details}')
                session.commit()
        return processed_ids

    @staticmethod
    def _launch_trusted_export_job():
        processed_ids = set()
        with db.session_scope() as session:
            trusted_jobs_ids = session.query(TrustedJob.id).filter_by(
                type=TrustedJobType.EXPORT,
                status=TrustedJobStatus.CREATED,
                coordinator_id=0,
            ).all()
        for trusted_job_id, *_ in trusted_jobs_ids:
            with db.session_scope() as session:
                tee_export_job = session.query(TrustedJob).get(trusted_job_id)
                if not tee_export_job.is_all_participants_authorized():
                    continue
            processed_ids.add(tee_export_job.id)
            succeeded, msg = launch_trusted_export_job(tee_export_job.project_id, tee_export_job.uuid)
            if not succeeded:
                with db.session_scope() as session:
                    tee_export_job = session.query(TrustedJob).get(trusted_job_id)
                    tee_export_job.status = TrustedJobStatus.FAILED
                    session.commit()
                logging.warning(f'[launch trusted export job scheduler]: {tee_export_job.id} failed, exception {msg}')
        return processed_ids

    @staticmethod
    def _create_export_dataset():
        processed_ids = set()
        with db.session_scope() as session:
            trusted_jobs_ids = session.query(TrustedJob.id).filter_by(
                type=TrustedJobType.EXPORT,
                status=TrustedJobStatus.SUCCEEDED,
                coordinator_id=0,
                export_dataset_id=None,
            ).all()
        for trusted_job_id, *_ in trusted_jobs_ids:
            with db.session_scope() as session:
                tee_export_job = session.query(TrustedJob).populate_existing().with_for_update().get(trusted_job_id)
                if tee_export_job.export_dataset_id:
                    continue
                processed_ids.add(tee_export_job.id)
                dataset = DatasetService(session).create_dataset(
                    dataset_pb2.DatasetParameter(
                        name=f'{tee_export_job.group.name}-{tee_export_job.name}',
                        is_published=False,
                        type=DatasetType.PSI.value,
                        project_id=tee_export_job.project_id,
                        kind=DatasetKindV2.INTERNAL_PROCESSED.value,
                        format=DatasetFormat.NONE_STRUCTURED.name,
                        path=f'{get_pure_path(Envs.STORAGE_ROOT)}/job_output/{tee_export_job.job.name}/export',
                        import_type=ImportType.COPY.value,
                        store_format=StoreFormat.UNKNOWN.value,
                        auth_status=AuthStatus.AUTHORIZED.name))
                session.flush()
                BatchService(session).create_batch(dataset_pb2.BatchParameter(dataset_id=dataset.id))
                tee_export_job.export_dataset_id = dataset.id
                session.commit()
        return processed_ids

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        # high-frequency runner compared to TEEAuthRunner do the following 4 tasks
        # 1. create trusted job groups with state is PENDING and ticket_status is APPROVED
        # 2. launch newly-self-created trusted jobs with version 0 and status SUCCEEDED when fully authed
        # 3. create remotely for local trusted export jobs with ticket_status APPROVED and status NEW
        # 4. launch trusted export jobs with coordinator_id 0 when fully created and authed
        # 5. create export dataset for successful trusted export job
        created_group_ids = self._create_trusted_job_group()
        launched_group_ids = self._launch_trusted_job()
        created_trusted_export_job_ids = self._create_trusted_export_job()
        launched_trusted_export_job_ids = self._launch_trusted_export_job()
        created_dataset_trusted_export_job_ids = self._create_export_dataset()
        return RunnerStatus.DONE, RunnerOutput(tee_runner_output=TeeRunnerOutput(
            created_group_ids=list(created_group_ids),
            launched_group_ids=list(launched_group_ids),
            created_trusted_export_job_ids=list(created_trusted_export_job_ids),
            launched_trusted_export_job_ids=list(launched_trusted_export_job_ids),
            created_dataset_trusted_export_job_ids=list(created_dataset_trusted_export_job_ids),
        ))


class TeeResourceCheckRunner(IRunnerV2):

    @staticmethod
    def _update_unauth_participant_ids():
        processed_groups = set()
        with db.session_scope() as session:
            group_ids = session.query(TrustedJobGroup.id).filter_by(status=GroupCreateStatus.SUCCEEDED).all()
        for group_id, *_ in group_ids:
            with db.session_scope() as session:
                group = session.query(TrustedJobGroup).populate_existing().with_for_update().get(group_id)
                TrustedJobGroupController(session, group.project_id).update_unauth_participant_ids(group)
                processed_groups.add(group_id)
                session.commit()
        return processed_groups

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        # low-frequency runner compared to TEECreateRunner do the following 2 tasks
        # 1. get auth_status of participants actively in case grpc InformTrustedJobGroup failed
        # 2. TODO(liuledian): get export_auth_status actively
        checked_group_ids = self._update_unauth_participant_ids()
        return RunnerStatus.DONE, RunnerOutput(tee_runner_output=TeeRunnerOutput(
            checked_group_ids=list(checked_group_ids)))
