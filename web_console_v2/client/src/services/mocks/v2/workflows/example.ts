import {
  WorkflowState,
  TransactionState,
  VariableAccessMode,
  JobDependencyType,
} from 'typings/workflow';

export const awaitParticipantConfig = {
  id: 1,
  name: 'put_test',
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

export const newlyCreated = {
  id: 2,
  name: 'Mocked Workflow → id: 2',
  project_id: 1,
  config: {
    group_alias: 'test-2',
    is_left: true,
    job_definitions: [
      {
        name: 'Initiative',
        type: 'RAW_DATA' as any,
        is_federated: true,
        variables: [
          {
            name: 'job_name',
            value: '1',
            access_mode: 'PEER_WRITABLE' as VariableAccessMode,
            widget_schema: '{"component":"Input","type":"string","required":true}' as any,
          },
        ],
        is_manual: false,
        dependencies: [],
        yaml_template: '',
      },
      {
        name: 'Raw data upload',
        type: 'RAW_DATA' as any,
        is_federated: true,
        variables: [
          {
            name: 'job_name2',
            value: '2',
            access_mode: 'PEER_WRITABLE' as VariableAccessMode,
            widget_schema: '{"component":"Input","type":"string"}' as any,
          },
          {
            name: 'comment2',
            value: '3',
            access_mode: 'PRIVATE' as VariableAccessMode,
            widget_schema: '{"component":"TextArea","rows":4,"type":"string","required":true}' as any,
          },
        ],
        dependencies: [{ source: 'Initiative', type: 'ON_COMPLETE' as JobDependencyType }],
        is_manual: false,
        yaml_template: '',
      },
      {
        name: 'Training',
        type: 'RAW_DATA',
        is_federated: true,
        variables: [
          {
            name: 'job_name2',
            value: '4',
            access_mode: 'PEER_WRITABLE' as VariableAccessMode,
            widget_schema: '{"component":"Input","type":"string"}',
          },
        ],
        dependencies: [{ source: 'Raw data upload', type: 'ON_COMPLETE' as JobDependencyType }],
        is_manual: false,
        yaml_template: '',
      },
    ],
    variables: [],
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
