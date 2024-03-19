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

from datetime import timedelta
import logging
import os
from typing import List
from sqlalchemy.orm import Session

from fedlearner_webconsole.db import db
from fedlearner_webconsole.cleanup.models import ResourceType
from fedlearner_webconsole.cleanup.services import CleanupService
from fedlearner_webconsole.composer.composer_service import ComposerService
from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.dataset.dataset_directory import DatasetDirectory
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobKind, DatasetJobStage, \
    DatasetJobSchedulerState, DatasetJobState, DataBatch, DatasetKindV2, DatasetType, ResourceState
from fedlearner_webconsole.dataset.scheduler.base_executor import BaseExecutor
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorResult
from fedlearner_webconsole.dataset.services import DatasetJobService, DatasetJobStageService, DatasetService
from fedlearner_webconsole.dataset.consts import ERROR_BATCH_SIZE
from fedlearner_webconsole.rpc.v2.resource_service_client import ResourceServiceClient
from fedlearner_webconsole.rpc.v2.system_service_client import SystemServiceClient
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.utils.pp_datetime import to_timestamp, now
from fedlearner_webconsole.utils.workflow import build_job_name
from fedlearner_webconsole.workflow.models import Workflow, WorkflowExternalState
from fedlearner_webconsole.flag.models import Flag
from fedlearner_webconsole.proto.cleanup_pb2 import CleanupParameter, CleanupPayload
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, BatchStatsInput

SIDE_OUTPUT_CLEANUP_DEFAULT_DELAY = timedelta(days=1)


class RunningDatasetJobStageExecutor(BaseExecutor):

    def _process_running_dataset_job_stage(self, session: Session,
                                           dataset_job_stage: DatasetJobStage) -> ExecutorResult:
        """Schedules running dataset job stage, same logic as _process_running_dataset_job.

        1. If the related workflow is completed
           - 1.1 Checks the batch stats item if it has been triggered.
             - 1.1.1 If the runner fails, then mark the job_stage as failed.
             - 1.1.2 If the runner completes, then mark the job_stage as succeeded.
           - 1.2 Triggers the batch stats item if it does not exist.
        2. If the related workflow is failed, then mark the job_stage as failed.
        """
        dataset_job_stage_service = DatasetJobStageService(session=session)
        workflow_state = dataset_job_stage.workflow.get_state_for_frontend()
        if workflow_state == WorkflowExternalState.COMPLETED:
            if not self._need_batch_stats(dataset_job_stage.dataset_job.kind):
                dataset_job_stage_service.finish_dataset_job_stage(dataset_job_stage=dataset_job_stage,
                                                                   finish_state=DatasetJobState.SUCCEEDED)
                return ExecutorResult.SUCCEEDED
            item_name = dataset_job_stage.get_context().batch_stats_item_name
            executor_result = ExecutorResult.SKIP
            if item_name:
                runners = ComposerService(session).get_recent_runners(item_name, count=1)
                if len(runners) > 0:
                    if runners[0].status == RunnerStatus.DONE.value:
                        self._set_data_batch_num_example(session, dataset_job_stage)
                        dataset_job_stage_service.finish_dataset_job_stage(dataset_job_stage=dataset_job_stage,
                                                                           finish_state=DatasetJobState.SUCCEEDED)
                        executor_result = ExecutorResult.SUCCEEDED
                    elif runners[0].status == RunnerStatus.FAILED.value:
                        batch = session.query(DataBatch).get(dataset_job_stage.data_batch_id)
                        # set file size to illegal value to let frontend know batch stats failed
                        batch.file_size = ERROR_BATCH_SIZE
                        session.flush()
                        self._set_data_batch_num_example(session, dataset_job_stage)
                        dataset_job_stage_service.finish_dataset_job_stage(dataset_job_stage=dataset_job_stage,
                                                                           finish_state=DatasetJobState.SUCCEEDED)
                        executor_result = ExecutorResult.SUCCEEDED
            else:
                item_name = f'batch_stats_{dataset_job_stage.data_batch.id}_{dataset_job_stage.id}'
                runner_input = RunnerInput(batch_stats_input=BatchStatsInput(batch_id=dataset_job_stage.data_batch.id))
                ComposerService(session).collect_v2(name=item_name, items=[(ItemType.BATCH_STATS, runner_input)])
                context = dataset_job_stage.get_context()
                context.batch_stats_item_name = item_name
                dataset_job_stage.set_context(context)
            return executor_result
        if workflow_state in (WorkflowExternalState.FAILED, WorkflowExternalState.STOPPED,
                              WorkflowExternalState.INVALID):
            dataset_job_stage_service.finish_dataset_job_stage(dataset_job_stage=dataset_job_stage,
                                                               finish_state=DatasetJobState.FAILED)
            return ExecutorResult.SUCCEEDED
        return ExecutorResult.SKIP

    def _process_succeeded_dataset_job_stage(self, session: Session, dataset_job_stage: DatasetJobStage):
        """Schedules when running dataset job stage succeeded, same logic as _process_succeeded_dataset_job.

        1. publish output_dataset if needed
        2. create transaction for participants
        3. delete side_output data
        """
        output_dataset: Dataset = dataset_job_stage.dataset_job.output_dataset
        meta_info = output_dataset.get_meta_info()
        if meta_info.need_publish:
            DatasetService(session).publish_dataset(dataset_id=output_dataset.id, value=meta_info.value)
            logging.info(f'[dataset_job_scheduler] auto publish dataset {output_dataset.id}')
            # set need_publish to false after publish
            meta_info.need_publish = False
            output_dataset.set_meta_info(meta_info)
        self._delete_side_output(session=session, dataset_job_stage=dataset_job_stage)

    def _process_failed_dataset_job_stage(self, session: Session, dataset_job_stage: DatasetJobStage):
        """Schedules when running dataset job stage failed.

        1. delete side_output data
        """
        self._delete_side_output(session=session, dataset_job_stage=dataset_job_stage)

    def _need_batch_stats(self, dataset_job_kind: DatasetJobKind):
        # batch sample info is now generated by analyzer spark task, so we need run again data stats after analyzer
        return dataset_job_kind in [
            DatasetJobKind.RSA_PSI_DATA_JOIN, DatasetJobKind.LIGHT_CLIENT_RSA_PSI_DATA_JOIN,
            DatasetJobKind.OT_PSI_DATA_JOIN, DatasetJobKind.LIGHT_CLIENT_OT_PSI_DATA_JOIN,
            DatasetJobKind.HASH_DATA_JOIN, DatasetJobKind.DATA_JOIN, DatasetJobKind.DATA_ALIGNMENT,
            DatasetJobKind.IMPORT_SOURCE, DatasetJobKind.ANALYZER
        ]

    def _get_single_batch_num_example(self, dataset: Dataset) -> int:
        try:
            return dataset.get_single_batch().num_example
        except TypeError as e:
            logging.info(f'single data_batch not found, err: {e}')
            return 0

    def _set_data_batch_num_example(self, session: Session, dataset_job_stage: DatasetJobStage):
        input_dataset: Dataset = dataset_job_stage.dataset_job.input_dataset
        if input_dataset.dataset_type == DatasetType.PSI:
            input_data_batch_num_example = self._get_single_batch_num_example(input_dataset)
        else:
            # TODO(liuhehan): add filter input data_batch by time_range
            input_data_batch = session.query(DataBatch).filter(DataBatch.dataset_id == input_dataset.id).filter(
                DataBatch.event_time == dataset_job_stage.event_time).first()
            input_data_batch_num_example = input_data_batch.num_example if input_data_batch else 0
        output_data_batch_num_example = dataset_job_stage.data_batch.num_example if dataset_job_stage.data_batch else 0
        context = dataset_job_stage.get_context()
        context.input_data_batch_num_example = input_data_batch_num_example
        context.output_data_batch_num_example = output_data_batch_num_example
        dataset_job_stage.set_context(context)

    def _delete_side_output(self, session: Session, dataset_job_stage: DatasetJobStage):
        output_dataset: Dataset = dataset_job_stage.dataset_job.output_dataset
        if output_dataset.dataset_kind not in [DatasetKindV2.RAW, DatasetKindV2.PROCESSED]:
            return
        batch_name = dataset_job_stage.data_batch.batch_name
        paths = [DatasetDirectory(output_dataset.path).side_output_path(batch_name)]
        # hack to get rsa_psi side_output
        # raw_data_path: raw_data_job side_output
        # psi_data_join_path: psi_data_join_job side_output, we only delete psi_output folder
        #                     as data_block folder is still used by model training
        if dataset_job_stage.dataset_job.kind == DatasetJobKind.RSA_PSI_DATA_JOIN:
            workflow: Workflow = dataset_job_stage.workflow
            raw_data_folder = build_job_name(workflow.uuid, 'raw-data-job')
            raw_data_path = os.path.join(workflow.project.get_storage_root_path(None), 'raw_data', raw_data_folder)
            psi_data_join_folder_name = build_job_name(workflow.uuid, 'psi-data-join-job')
            psi_data_join_path = os.path.join(workflow.project.get_storage_root_path(None), 'data_source',
                                              psi_data_join_folder_name, 'psi_output')
            paths.extend([raw_data_path, psi_data_join_path])
        target_start_at = to_timestamp(now() + SIDE_OUTPUT_CLEANUP_DEFAULT_DELAY)
        cleanup_param = CleanupParameter(resource_id=dataset_job_stage.id,
                                         resource_type=ResourceType.DATASET_JOB_STAGE.name,
                                         payload=CleanupPayload(paths=paths),
                                         target_start_at=target_start_at)
        CleanupService(session).create_cleanup(cleanup_parmeter=cleanup_param)

    def get_item_ids(self) -> List[int]:
        with db.session_scope() as session:
            running_dataset_job_stage_ids = session.query(DatasetJobStage.id).outerjoin(
                DatasetJob, DatasetJob.id == DatasetJobStage.dataset_job_id).filter(
                    DatasetJobStage.state == DatasetJobState.RUNNING).filter(
                        DatasetJob.scheduler_state != DatasetJobSchedulerState.PENDING).all()
        return [running_dataset_job_stage_id for running_dataset_job_stage_id, *_ in running_dataset_job_stage_ids]

    def run_item(self, item_id: int) -> ExecutorResult:
        with db.session_scope() as session:
            # we set isolation_level to SERIALIZABLE to make sure state won't be changed within this session
            session.connection(execution_options={'isolation_level': 'SERIALIZABLE'})
            dataset_job_stage: DatasetJobStage = session.query(DatasetJobStage).get(item_id)
            if dataset_job_stage.state != DatasetJobState.RUNNING:
                return ExecutorResult.SKIP
            executor_result = self._process_running_dataset_job_stage(session, dataset_job_stage)
            if dataset_job_stage.state == DatasetJobState.SUCCEEDED:
                self._process_succeeded_dataset_job_stage(session, dataset_job_stage)
            elif dataset_job_stage.state == DatasetJobState.FAILED:
                self._process_failed_dataset_job_stage(session, dataset_job_stage)
            session.commit()
        return executor_result
