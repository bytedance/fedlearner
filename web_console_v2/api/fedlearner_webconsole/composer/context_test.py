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

from fedlearner_webconsole.composer.context import PipelineContext
from fedlearner_webconsole.proto.composer_pb2 import Pipeline, RunnerInput, PipelineContextData


class PipelineContextTest(unittest.TestCase):

    def test_get_current_runner_context(self):
        pipeline_context = PipelineContext.build(pipeline=Pipeline(version=2,
                                                                   name='test pipeline',
                                                                   queue=[
                                                                       RunnerInput(runner_type='test type1'),
                                                                       RunnerInput(runner_type='test type2'),
                                                                   ]),
                                                 data=PipelineContextData())
        runner_context = pipeline_context.get_current_runner_context()
        self.assertEqual(runner_context.index, 0)
        self.assertEqual(runner_context.input.runner_type, 'test type1')
        pipeline_context.run_next()
        runner_context = pipeline_context.get_current_runner_context()
        self.assertEqual(runner_context.index, 1)
        self.assertEqual(runner_context.input.runner_type, 'test type2')
        # No effect as whole pipeline already done
        pipeline_context.run_next()
        runner_context = pipeline_context.get_current_runner_context()
        self.assertEqual(runner_context.index, 1)


if __name__ == '__main__':
    unittest.main()
