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
# pylint: disable=cyclic-import
from http import HTTPStatus
from flask_restful import Resource, abort
from fedlearner_webconsole.workflow.models import Workflow



class WorkflowListApi(Resource):
    def get(self):
        return {'data': [row.to_dict() for row in Workflow.query.all()]}

    def post(self):
        # TODO: create workflow
        pass


class WorkflowApi(Resource):
    def get(self, workflow_id):
        result = Workflow.query.filter_by(id=workflow_id).first()
        if result is None:
            abort(HTTPStatus.BAD_REQUEST,
                  msg='The workflow is not existed')
        return {'data': result.to_dict()}


# TODO: fork method to get templates by workflowid


def initialize_workflow_apis(api):
    api.add_resource(WorkflowListApi, '/workflows')
    api.add_resource(WorkflowApi, '/workflows/<int:workflow_id>')
