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

from fedlearner_webconsole.dataset.metrics import emit_dataset_job_submission_store, emit_dataset_job_duration_store
from fedlearner_webconsole.dataset.models import DatasetJobKind, DatasetJobState


class MetricsTest(unittest.TestCase):

    def test_emit_dataset_job_submission_store(self):
        with self.assertLogs() as cm:
            emit_dataset_job_submission_store('uuit-test', DatasetJobKind.IMPORT_SOURCE, 0)
            logs = [r.msg for r in cm.records]
            self.assertEqual(logs, [
                '[Metric][Store] dataset.job.submission: 1, tags={\'uuid\': \'uuit-test\', ' \
                    '\'kind\': \'IMPORT_SOURCE\', \'coordinator_id\': \'0\'}',
            ])

    def test_emit_dataset_job_duration_store(self):
        with self.assertLogs() as cm:
            emit_dataset_job_duration_store(1000, 'uuit-test', DatasetJobKind.RSA_PSI_DATA_JOIN, 1,
                                            DatasetJobState.SUCCEEDED)
            logs = [r.msg for r in cm.records]
            self.assertEqual(logs, [
                '[Metric][Store] dataset.job.duration: 1000, tags={\'uuid\': \'uuit-test\', ' \
                    '\'kind\': \'RSA_PSI_DATA_JOIN\', \'coordinator_id\': \'1\', \'state\': \'SUCCEEDED\'}',
            ])


if __name__ == '__main__':
    unittest.main()
