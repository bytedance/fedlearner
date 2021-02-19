import { cloneDeep } from 'lodash';
import { JobExecutionDetalis, JobState, JobType, PodState } from 'typings/job';
import {
  WorkflowState,
  TransactionState,
  WorkflowExecutionDetails,
  Workflow,
} from 'typings/workflow';
import { VariableAccessMode } from 'typings/variable';
import { normalTemplate } from '../workflow_templates/examples';

export const awaitParticipantConfig = {
  id: 1,
  name: 'Await-configure',
  project_id: 1,
  config: null,
  forkable: true,
  comment: null,
  state: WorkflowState.NEW,
  target_state: WorkflowState.READY,
  transaction_state: TransactionState.PARTICIPANT_PREPARE,
  transaction_err: null,
  created_at: 1610238602,
  updated_at: 1610238602,
};

export const newlyCreated: Workflow = {
  id: 2,
  name: 'Newly-created',
  project_id: 1,
  config: {
    group_alias: 'test-2',
    is_left: true,
    job_definitions: [
      {
        name: 'Initiative',
        job_type: 'RAW_DATA' as any,
        is_federated: true,
        variables: [
          {
            name: 'job_name',
            value: '1',
            access_mode: 'PEER_READABLE' as VariableAccessMode,
            widget_schema: '{"component":"Input","type":"string","required":true}' as any,
          },
        ],
        is_manual: false,
        dependencies: [],
        yaml_template: '',
      },
      {
        name: 'Raw data upload',
        job_type: 'RAW_DATA' as any,
        is_federated: true,
        variables: [
          {
            name: 'job_name2',
            value: '2',
            access_mode: 'PEER_WRITABLE' as VariableAccessMode,
            widget_schema: '{"component":"Input","type":"string","required":true}' as any,
          },
          {
            name: 'comment2',
            value: '3',
            access_mode: 'PRIVATE' as VariableAccessMode,
            widget_schema: '{"component":"TextArea","rows":4,"type":"string","required":true}' as any,
          },
        ],
        dependencies: [{ source: 'Initiative' }],
        is_manual: false,
        yaml_template: '',
      },
      {
        name: 'Training',
        job_type: 'RAW_DATA',
        is_federated: true,
        variables: [
          {
            name: 'job_name2',
            value: '4',
            access_mode: 'PEER_WRITABLE' as VariableAccessMode,
            widget_schema: '{"component":"Input","type":"string"}',
          },
        ],
        dependencies: [{ source: 'Raw data upload' }],
        is_manual: false,
        yaml_template: '',
      },
    ],
    variables: [
      {
        name: 'image_version',
        value: 'v1.5-rc3',
        access_mode: VariableAccessMode.PEER_READABLE,
        widget_schema: '{"required": true}' as any,
      },
    ],
  },
  forkable: true,
  comment: null,
  state: WorkflowState.NEW,
  target_state: WorkflowState.READY,
  transaction_state: TransactionState.COORDINATOR_COMMITTABLE,
  transaction_err: null,
  created_at: 1610239831,
  updated_at: 1610239831,
};

export const withExecutionDetail: WorkflowExecutionDetails = {
  ...cloneDeep(newlyCreated),
  run_time: 100000, // second level
  jobs: _generateJobExecutionDetails('With-execution-details'),
};

export const completed = {
  ...cloneDeep(withExecutionDetail),
  id: 3,
  name: 'All-completed',
  config: normalTemplate.data.config as any,
  state: WorkflowState.COMPLETED,
  target_state: WorkflowState.INVALID,
  transaction_state: TransactionState.ABORTED,
  jobs: _generateJobExecutionDetails('All-completed'),
};

function _generateJobExecutionDetails(workflowName: string): JobExecutionDetalis[] {
  return [
    {
      id: 1,
      name: `${workflowName}-Initiative`,
      job_type: JobType.RAW_DATA,
      state: JobState.COMPLETE,
      yaml_template: '',
      workflow_id: 1,
      project_id: 1,
      pods: [],
      created_at: 1611006571,
      updated_at: 1611006571,
      deleted_at: 0,
    },
    {
      id: 2,
      name: `${workflowName}-Raw data upload`,
      job_type: JobType.DATA_JOIN,
      state: JobState.RUNNING,
      yaml_template: '',
      workflow_id: 1,
      project_id: 1,
      pods: [
        {
          name: '0-79f60e7a-520e-4cd7-a679-95b12df2c4fd',
          pod_type: 'Master',
          status: PodState.COMPLETE,
        },
      ],
      created_at: 1611006571,
      updated_at: 1611006571,
      deleted_at: 0,
    },
    {
      id: 3,
      name: `${workflowName}-Training`,
      job_type: JobType.DATA_JOIN,
      state: JobState.STOPPED,
      yaml_template: '',
      workflow_id: 1,
      project_id: 1,
      pods: [],
      created_at: 1611006571,
      updated_at: 1611006571,
      deleted_at: 0,
    },
  ];
}
