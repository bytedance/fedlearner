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

from datetime import datetime
import unittest
from unittest.mock import MagicMock, patch

from testing.no_web_server_test_case import NoWebServerTestCase

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import Dataset, DatasetKindV2, ImportType, DatasetType, DataBatch
from fedlearner_webconsole.dataset.data_path import get_batch_data_path
from fedlearner_webconsole.utils.resource_name import resource_uuid


class DataPathTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            dataset = Dataset(id=1,
                              uuid=resource_uuid(),
                              name='default dataset',
                              dataset_type=DatasetType.PSI,
                              comment='test comment',
                              path='/data/dataset/123',
                              project_id=1,
                              created_at=datetime(2012, 1, 14, 12, 0, 5),
                              dataset_kind=DatasetKindV2.RAW,
                              is_published=False,
                              import_type=ImportType.NO_COPY)
            session.add(dataset)
            data_batch = DataBatch(id=1,
                                   name='20220701',
                                   dataset_id=1,
                                   path='/data/test/batch/20220701',
                                   event_time=datetime.strptime('20220701', '%Y%m%d'),
                                   file_size=100,
                                   num_example=10,
                                   num_feature=3,
                                   latest_parent_dataset_job_stage_id=1)
            session.add(data_batch)
            session.commit()

    @patch('fedlearner_webconsole.dataset.data_path.FileManager.read')
    def test_get_batch_data_path(self, mock_read: MagicMock):
        source_path = '/data/data_source/batch_1'
        mock_read.return_value = source_path
        # test get data_path when import_type is NO_COPY
        with db.session_scope() as session:
            data_batch: DataBatch = session.query(DataBatch).get(1)
            self.assertEqual(get_batch_data_path(data_batch), source_path)
            mock_read.assert_called_once_with('/data/dataset/123/batch/20220701/source_batch_path')
        # test get data_path when import_type is COPY
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(1)
            dataset.import_type = ImportType.COPY
            session.commit()
        with db.session_scope() as session:
            data_batch: DataBatch = session.query(DataBatch).get(1)
            self.assertEqual(get_batch_data_path(data_batch), data_batch.path)


if __name__ == '__main__':
    unittest.main()
