import { JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import { Job, JobExecutionDetalis, CreateJobFlag } from './job';
import { Variable } from './variable';

export type WorkflowConfig<J = Job> = {
  group_alias: string;
  is_left: boolean;
  variables: Variable[];
  job_definitions: J[];
};

export type ChartWorkflowConfig = WorkflowConfig<JobNodeRawData>;

export interface WorkflowTemplate<J = Job> {
  id: number;
  name: string;
  is_left: boolean;
  group_alias: string;
  comment?: string;
  config: WorkflowConfig<J>;
}

export type WorkflowTemplatePayload<J = Job> = {
  name: string;
  is_left?: boolean;
  group_alias?: string;
  comment?: string;
  config: WorkflowConfig<J>;
};

export type WorkflowInitiatePayload = {
  name: string;
  project_id: ID;
  forkable: boolean;
  batch_update_interval?: number;
  create_job_flags?: CreateJobFlag[];
  config: ChartWorkflowConfig;
  comment?: string;
};

export type WorkflowAcceptPayload = {
  forkable: boolean;
  create_job_flags?: CreateJobFlag[];
  batch_update_interval?: number;
  config: ChartWorkflowConfig;
  comment?: string;
};

export type WorkflowForkPayload = WorkflowInitiatePayload & {
  forked_from: ID;
  batch_update_interval?: number;
  create_job_flags: CreateJobFlag[]; // e.g. [raw_data, training...]
  peer_create_job_flags: CreateJobFlag[];
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
  metric_is_public?: boolean;
  forked_from?: number;
  comment: string | null;
  state: WorkflowState;
  target_state: WorkflowState;
  transaction_state: TransactionState;
  transaction_err: string | null;
  created_at: DateTime;
  updated_at: DateTime;
  batch_update_interval?: number;
  start_at?: DateTime | null;
  stop_at?: DateTime | null;
};

export type WorkflowExecutionDetails = {
  uuid: string;
  jobs: JobExecutionDetalis[];
  run_time: number;
  create_job_flags?: CreateJobFlag[];
  peer_create_job_flags?: CreateJobFlag[];
} & Workflow;
