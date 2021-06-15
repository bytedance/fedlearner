import { cloneDeep, sample } from 'lodash';
import { JobExecutionDetalis, JobState, JobType, Pod, PodState } from 'typings/job';
import {
  WorkflowState,
  TransactionState,
  WorkflowExecutionDetails,
  Workflow,
} from 'typings/workflow';
import { VariableAccessMode } from 'typings/variable';
import { normalTemplate } from '../workflow_templates/examples';

const uuid_1 = '9d73398659927';
export const pendingAcceptAndConfig = {
  id: 1,
  uuid: uuid_1,
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

const uuid_2 = '8d733986594343';
export const newlyCreated: Workflow = {
  id: 2,
  uuid: uuid_2,
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

const uuid_3 = '7d73398659927';

export const withExecutionDetail: WorkflowExecutionDetails = {
  ...cloneDeep(newlyCreated),
  uuid: uuid_3,
  metric_is_public: true,
  run_time: 100000, // second level
  jobs: _generateJobExecutionDetails(uuid_3),
};

const uuid_4 = '67d7339865992';

export const completed = {
  ...cloneDeep(withExecutionDetail),
  id: 3,
  uuid: uuid_4,
  name: 'All-completed',
  config: normalTemplate.config as any,
  state: WorkflowState.COMPLETED,
  target_state: WorkflowState.INVALID,
  transaction_state: TransactionState.ABORTED,
  jobs: _generateJobExecutionDetails(uuid_4),
};

function _generateJobExecutionDetails(UUID: string): JobExecutionDetalis[] {
  return [
    {
      id: 1,
      name: `${UUID}-Initiative`,
      job_type: JobType.RAW_DATA,
      state: JobState.COMPLETED,
      yaml_template: '',
      workflow_id: 1,
      project_id: 1,
      pods: [_genPod(), _genPod(), _genPod()],
      created_at: 1611006571,
      updated_at: 1611006571,
      deleted_at: 0,
    },
    {
      id: 2,
      name: `${UUID}-Raw data upload`,
      job_type: JobType.DATA_JOIN,
      state: JobState.STARTED,
      yaml_template: '',
      workflow_id: 1,
      project_id: 1,
      pods: [_genPod(), _genPod()],
      created_at: 1611006571,
      updated_at: 1611006571,
      deleted_at: 0,
    },
    {
      id: 3,
      name: `${UUID}-Raw data process`,
      job_type: JobType.DATA_JOIN,
      state: JobState.STOPPED,
      yaml_template: '',
      workflow_id: 1,
      project_id: 1,
      pods: [_genPod(), _genPod(), _genPod(), _genPod()],
      created_at: 1611006571,
      updated_at: 1611006571,
      deleted_at: 0,
    },
  ];
}

function _genPod() {
  return {
    name: `0-79f60e7a-520e-4cd7-a679-sada2e21hjklhds8s`,
    pod_ip: '172.10.0.20',
    pod_type: 'Master',
    state: sample(PodState),
    message: '0/3 nodes are available: 3 Insufficient cpu.',
  } as Pod;
}
