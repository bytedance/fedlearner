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
import logging
import threading
import os
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import timedelta, datetime

from fedlearner_webconsole.dataset.models import DataBatch, BatchState
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.proto import dataset_pb2

class ImportHandler(object):
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=os.cpu_count() * 3)
        self._file_manager = FileManager()
        self._pending_imports = set()
        self._running_imports = set()
        self._import_lock = threading.Lock()
        self._app = None

    def __del__(self):
        self._executor.shutdown()

    def init(self, app):
        self._app = app

    def schedule_to_handle(self, dataset_batch_ids):
        if isinstance(dataset_batch_ids, int):
            dataset_batch_ids = [dataset_batch_ids]
        self._pending_imports.update(dataset_batch_ids)

    def _copy_file(self, source_path, destination_path,
                   move=False, num_retry=3):
        logging.info('%s from %s to %s',
                     'moving' if move else 'copying',
                     source_path,
                     destination_path)
        # Creates parent folders if needed
        parent_folder = os.path.dirname(destination_path)
        self._file_manager.mkdir(parent_folder)
        success = False
        error_message = ''
        for _ in range(num_retry):
            try:
                if move:
                    success = self._file_manager.move(
                        source_path,
                        destination_path)
                else:
                    success = self._file_manager.copy(
                        source_path,
                        destination_path)
                if not success:
                    error_message = 'Unknown error'
                else:
                    break
            except Exception as e:  # pylint: disable=broad-except
                logging.error(
                    'Error occurred when importing file from %s to %s',
                    source_path,
                    destination_path)
                error_message = str(e)
        file = dataset_pb2.File(
            source_path=source_path,
            destination_path=destination_path
        )
        if not success:
            file.error_message = error_message
            file.state = dataset_pb2.File.State.FAILED
        else:
            file.size = self._file_manager.ls(
                destination_path)[0]['size']
            file.state = dataset_pb2.File.State.COMPLETED
        return file

    def _import_batch(self, batch_id):
        self._import_lock.acquire()
        if batch_id in self._running_imports:
            return
        self._running_imports.add(batch_id)
        self._import_lock.release()

        # Pushes app context to make db session work
        self._app.app_context().push()

        logging.info('Importing batch %d', batch_id)
        batch = DataBatch.query.get(batch_id)
        batch.state = BatchState.IMPORTING
        db.session.commit()
        db.session.refresh(batch)
        details = batch.get_details()

        for file in details.files:
            if file.state == dataset_pb2.File.State.UNSPECIFIED:
                # Recovers the state
                destination_existed = len(
                    self._file_manager.ls(file.destination_path)) > 0
                if destination_existed:
                    file.state = dataset_pb2.File.State.COMPLETED
                    continue
                # Moves/Copies
                file.MergeFrom(self._copy_file(
                    source_path=file.source_path,
                    destination_path=file.destination_path,
                    move=batch.move))

        batch.set_details(details)
        db.session.commit()

        self._import_lock.acquire()
        self._running_imports.remove(batch_id)
        self._import_lock.release()


    def handle(self, pull=False):
        """Handles all the batches in the queue or all batches which
        should be imported."""
        batches_to_run = self._pending_imports
        self._pending_imports = set()
        if pull:
            # TODO: should separate pull logic to a cron job,
            # otherwise there will be a race condition that two handlers
            # are trying to move the same batch
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            pulled_batches = db.session.query(DataBatch.id).filter(
                    (DataBatch.state == BatchState.NEW) |
                    (DataBatch.state == BatchState.IMPORTING))\
                .filter(DataBatch.updated_at < one_hour_ago)\
                .all()
            pulled_ids = [bid for bid, in pulled_batches]
            batches_to_run.update(pulled_ids)

        for batch in batches_to_run:
            self._executor.submit(self._import_batch, batch)
