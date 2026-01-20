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

# pylint: disable=redefined-builtin
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, PipelineContextData, Pipeline


class RunnerContext(object):

    def __init__(self, index: int, input: RunnerInput):
        self._index = index
        self._input = input

    @property
    def index(self) -> int:
        return self._index

    @property
    def input(self) -> RunnerInput:
        return self._input


class PipelineContext(object):

    def __init__(self, pipeline: Pipeline, data: PipelineContextData):
        self._pipeline = pipeline
        self._data = data
        self._runner_contexts = {}

    @classmethod
    def build(cls, pipeline: Pipeline, data: PipelineContextData) -> 'PipelineContext':
        return cls(pipeline=pipeline, data=data)

    def run_next(self):
        if self._data.current_runner >= len(self._pipeline.queue) - 1:
            return
        self._data.current_runner += 1

    def get_current_runner_context(self) -> RunnerContext:
        runner_idx = self._data.current_runner
        if runner_idx in self._runner_contexts:
            return self._runner_contexts[runner_idx]
        context = RunnerContext(index=runner_idx, input=self._pipeline.queue[runner_idx])
        self._runner_contexts[runner_idx] = context
        return context

    @property
    def data(self) -> PipelineContextData:
        return self._data
