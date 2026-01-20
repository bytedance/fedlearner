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
from typing import Tuple, List
from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.interface import IRunnerV2
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.proto.composer_pb2 import RunnerOutput, CleanupCronJobOutput
from datetime import timezone, datetime
from fedlearner_webconsole.cleanup.models import Cleanup, CleanupState


class CleanupCronJob(IRunnerV2):

    def __init__(self) -> None:
        super().__init__()
        self._file_manager = FileManager()

    def _get_current_utc_time(self):
        return datetime.now(tz=timezone.utc)

    def _execute_cleanup(self, cleanup: Cleanup):
        for path in cleanup.payload.paths:
            if self._file_manager.exists(path):
                self._file_manager.remove(path)
        cleanup.state = CleanupState.SUCCEEDED
        cleanup.completed_at = self._get_current_utc_time()

    def _get_waiting_ids(self) -> List[int]:
        with db.session_scope() as session:
            current_time = self._get_current_utc_time()
            waiting_ids = session.query(Cleanup.id).filter(Cleanup.state == CleanupState.WAITING).filter(
                Cleanup.target_start_at <= current_time).all()
            logging.info(f'Has collected waiting cleanup ids:{waiting_ids}')
            # unwrap query result
            return [cleanup_id for cleanup_id, *_ in waiting_ids]

    def _sweep_waiting_cleanups(self, waiting_list: List[int]):
        logging.info(f'will sweep the cleanup ids:{waiting_list}')
        for cleanup_id in waiting_list:
            with db.session_scope() as session:
                logging.info(f'will sweep the waiting cleanup:{cleanup_id}')
                current_time = self._get_current_utc_time()
                cleanup = session.query(Cleanup).populate_existing().with_for_update().get(cleanup_id)
                try:
                    if cleanup and cleanup.state == CleanupState.WAITING and \
                        cleanup.target_start_at.replace(tzinfo=timezone.utc) <= current_time:
                        cleanup.state = CleanupState.RUNNING
                        # Release the lock
                        session.commit()
                    else:
                        logging.warning(f'In waiting cleanup list are being swept, \
                                 the cleanup:{cleanup_id} has been changed/canceled. It has been skipped.')
                        # Release the lock
                        session.rollback()
                except Exception as e:  # pylint: disable=broad-except
                    logging.error(f'The cleanup:{cleanup.id} has failed. error_msg is:{str(e)}')
                    cleanup.state = CleanupState.FAILED
                    session.commit()

    def _get_running_ids(self) -> List[int]:
        with db.session_scope() as session:
            running_ids = session.query(Cleanup.id).filter(Cleanup.state == CleanupState.RUNNING).all()
            logging.info(f'Has collected waiting cleanup ids:{running_ids}')
            # unwrap query result
            return [cleanup_id for cleanup_id, *_ in running_ids]

    def _sweep_running_cleanups(self, running_list: List[int]) -> Tuple[List[int], List[int]]:
        logging.info(f'will sweep the cleanup ids:{running_list}')
        succeeded_cleanup_ids = []
        failed_cleanup_ids = []
        for cleanup_id in running_list:
            with db.session_scope() as session:
                logging.info(f'will sweep the running cleanup:{cleanup_id}')
                cleanup = session.query(Cleanup).populate_existing().with_for_update().get(cleanup_id)
                try:
                    if cleanup and cleanup.state == CleanupState.RUNNING:
                        self._execute_cleanup(cleanup)
                        # Release the lock
                        session.commit()
                        succeeded_cleanup_ids.append(cleanup.id)
                    else:
                        logging.warning(f'In running cleanup list are being swept, \
                                 the cleanup:{cleanup_id} has been changed/canceled. It has been skipped.')
                        # Release the lock
                        session.rollback()
                except Exception as e:  # pylint: disable=broad-except
                    logging.error(f'The cleanup:{cleanup.id} has failed. error_msg is:{str(e)}')
                    cleanup.state = CleanupState.FAILED
                    session.commit()
                    failed_cleanup_ids.append(cleanup.id)
        return succeeded_cleanup_ids, failed_cleanup_ids

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        try:
            waiting_ids = self._get_waiting_ids()
            self._sweep_waiting_cleanups(waiting_ids)
            running_ids = self._get_running_ids()
            succeeded_cleanup_ids, failed_cleanup_ids = self._sweep_running_cleanups(running_ids)
            return RunnerStatus.DONE, RunnerOutput(cleanup_cron_job_output=CleanupCronJobOutput(
                succeeded_cleanup_ids=succeeded_cleanup_ids, failed_cleanup_ids=failed_cleanup_ids))
        except Exception as e:  # pylint: disable=broad-except
            logging.error(f'Cleanup Cronjob is failed. error_msg is:{str(e)}')
            return RunnerStatus.FAILED, RunnerOutput(error_message=str(e))
