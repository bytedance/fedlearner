import { NodeDataRaw } from 'components/WorkflowJobsFlowChart/types';
import { Job, JobExecutionDetalis } from './job';
import { Variable } from './variable';

export type WorkflowConfig<J = Job> = {
  group_alias: string;
  is_left: boolean;
  variables: Variable[];
  job_definitions: J[];
};

export type ChartWorkflowConfig = WorkflowConfig<NodeDataRaw>;

export interface WorkflowTemplate {
  id: number;
  name: string;
  comment: string;
  is_left: boolean;
  group_alias: string;
  config: WorkflowConfig;
}

export type WorkflowTemplatePayload = {
  name: string;
  is_left?: boolean;
  group_alias?: string;
  comment?: string;
  config: WorkflowConfig;
};

export type WorkflowInitiatePayload = {
  name: string;
  project_id: ID;
  forkable: boolean;
  config: ChartWorkflowConfig;
  comment?: string;
};

export type WorkflowAcceptPayload = {
  forkable: boolean;
  config: ChartWorkflowConfig;
  comment?: string;
};

export type WorkflowForkPayload = WorkflowInitiatePayload & {
  forked_from: ID;
  reuse_job_names: string[]; // e.g. [raw_data, training...]
  peer_reuse_job_names: string[];
  fork_proposal_config: ChartWorkflowConfig;
};

export enum WorkflowState {
  INVALID = 'INVALID',
  NEW = 'NEW',
  READY = 'READY',
  RUNNING = 'RUNNING',
  STOPPED = 'STOPPED',
  FAILED = 'FAILED',
  COMPLETED = 'COMPLETED',
}

export enum TransactionState {
  READY = 'READY',
  ABORTED = 'ABORTED',

  COORDINATOR_PREPARE = 'COORDINATOR_PREPARE',
  COORDINATOR_COMMITTABLE = 'COORDINATOR_COMMITTABLE',
  COORDINATOR_COMMITTING = 'COORDINATOR_COMMITTING',
  COORDINATOR_ABORTING = 'COORDINATOR_ABORTING',

  PARTICIPANT_PREPARE = 'PARTICIPANT_PREPARE',
  PARTICIPANT_COMMITTABLE = 'PARTICIPANT_COMMITTABLE',
  PARTICIPANT_COMMITTING = 'PARTICIPANT_COMMITTING',
  PARTICIPANT_ABORTING = 'PARTICIPANT_ABORTING',
}

export type Workflow = {
  id: number;
  uuid?: string;
  name: string;
  project_id: number;
  config: WorkflowConfig | null;
  forkable: boolean;
  forked_from?: number;
  comment: string | null;
  state: WorkflowState;
  target_state: WorkflowState;
  transaction_state: TransactionState;
  transaction_err: string | null;
  created_at: DateTime;
  updated_at: DateTime;
  start_at?: DateTime | null;
  stop_at?: DateTime | null;
};

export type WorkflowExecutionDetails = {
  uuid: string;
  jobs: JobExecutionDetalis[];
  run_time: number;
  reuse_job_names?: string[];
  peer_reuse_job_names?: string[];
} & Workflow;
