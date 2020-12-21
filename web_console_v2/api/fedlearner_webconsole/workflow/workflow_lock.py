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
from multiprocessing.managers import BaseManager, RemoteError


class WorkflowManager(BaseManager):
    pass


class WorkflowLock:
    def __init__(self):
        self.workflow_mutex = {}

    def lock(self, workflow, prepare_status):
        if workflow.uuid in self.workflow_mutex \
             and self.workflow_mutex[workflow.uuid]:
            raise RemoteError('The workflow status is being modified')
        if workflow.status not in prepare_status:
            raise RemoteError(
                'The workflow status need to be {} but {}'
                    .format(prepare_status, workflow.status))
        self.workflow_mutex[workflow.uuid] = True

    def release(self, workflow):
        print(workflow.uuid)
        self.workflow_mutex[workflow.uuid] = False


port = 1991
workflow_lock = WorkflowLock()


def workflow_manager_start():
    WorkflowManager.register('workflow_lock', callable=lambda: workflow_lock)
    workflow_manager = WorkflowManager(address=('127.0.0.1', port),
                                       authkey=b'workflow_manager')
    s = workflow_manager.get_server()
    s.serve_forever()


def get_worklow_lock():
    WorkflowManager.register('workflow_lock')
    workflow_manager = WorkflowManager(address=('', port),
                                       authkey=b'workflow_manager')
    workflow_manager.connect()
    result = workflow_manager.workflow_lock()
    return result


if __name__ == '__main__':
    workflow_manager_start()
