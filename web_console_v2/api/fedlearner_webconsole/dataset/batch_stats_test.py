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

import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from multiprocessing import Queue

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.dataset.batch_stats import BatchStatsRunner, batch_stats_sub_process
from fedlearner_webconsole.dataset.models import DataBatch, Dataset, BatchState, DatasetType
from fedlearner_webconsole.dataset.services import DataReader
from fedlearner_webconsole.db import db, turn_db_timezone_to_utc
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, BatchStatsInput
from testing.no_web_server_test_case import NoWebServerTestCase


def fake_batch_stats_sub_process(batch_id: int, q: Queue):
    q.put([10, 666, 789123])


class BatchStatsRunnerTest(NoWebServerTestCase):

    @patch('fedlearner_webconsole.dataset.batch_stats.batch_stats_sub_process', fake_batch_stats_sub_process)
    def test_run_for_batch(self):
        with db.session_scope() as session:
            dataset = Dataset(id=1, name='test_dataset', path='/test_dataset', dataset_type=DatasetType.PSI)
            session.add(dataset)
            batch = DataBatch(id=2,
                              name='0',
                              dataset_id=dataset.id,
                              path='/test_dataset/1/batch/0',
                              event_time=datetime(2021, 10, 28, 16, 37, 37))
            session.add(batch)
            session.commit()

        runner = BatchStatsRunner()

        runner_input = RunnerInput(batch_stats_input=BatchStatsInput(batch_id=2))
        context = RunnerContext(index=0, input=runner_input)

        # Succeeded case
        status, _ = runner.run(context)
        self.assertEqual(status, RunnerStatus.DONE)
        with db.session_scope() as session:
            batch = session.query(DataBatch).get(2)
            self.assertEqual(batch.state, BatchState.SUCCESS)
            self.assertEqual(batch.num_feature, 10)
            self.assertEqual(batch.num_example, 666)
            self.assertEqual(batch.file_size, 789123)

    @patch('fedlearner_webconsole.dataset.batch_stats.FileOperator.getsize')
    @patch('fedlearner_webconsole.dataset.batch_stats.DataReader')
    @patch('fedlearner_webconsole.dataset.services.DataReader.metadata')
    @patch('fedlearner_webconsole.utils.hooks.get_database_uri')
    def test_batch_stats_sub_process(self, mock_get_database_uri: MagicMock, mock_metadata: MagicMock,
                                     mock_data_reader: MagicMock, mock_getsize: MagicMock):
        with db.session_scope() as session:
            dataset = Dataset(id=1, name='test_dataset', path='/test_dataset', dataset_type=DatasetType.PSI)
            session.add(dataset)
            batch = DataBatch(id=2,
                              name='0',
                              dataset_id=dataset.id,
                              path='/test_dataset/1/batch/0',
                              event_time=datetime(2021, 10, 28, 16, 37, 37))
            session.add(batch)
            session.commit()
        mock_metadata_res = MagicMock()
        mock_metadata_res.num_feature = 10
        mock_metadata_res.num_example = 666
        mock_getsize.return_value = 789123
        mock_get_database_uri.return_value = turn_db_timezone_to_utc(self.__class__.Config.SQLALCHEMY_DATABASE_URI)

        mock_data_reader.return_value = DataReader('/test_dataset')
        mock_metadata.return_value = mock_metadata_res

        queue = Queue()
        batch_stats_sub_process(batch_id=2, q=queue)
        batch_num_feature, batch_num_example, batch_file_size = queue.get()
        self.assertEqual(batch_num_feature, 10)
        self.assertEqual(batch_num_example, 666)
        self.assertEqual(batch_file_size, 789123)


if __name__ == '__main__':
    unittest.main()
