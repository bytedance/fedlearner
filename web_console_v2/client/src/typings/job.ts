import { Variable } from './variable';

export enum JobState {
  INVALID = 'INVALID',
  NEW = 'NEW',
  WAITING = 'WAITING',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  STOPPED = 'STOPPED',
}

export enum JobType {
  UNSPECIFIED = 'UNSPECIFIED',
  RAW_DATA = 'RAW_DATA',
  DATA_JOIN = 'DATA_JOIN',
  PSI_DATA_JOIN = 'PSI_DATA_JOIN',
  NN_MODEL_TRANINING = 'NN_MODEL_TRANINING',
  TREE_MODEL_TRAINING = 'TREE_MODEL_TRAINING',
  NN_MODEL_EVALUATION = 'NN_MODEL_EVALUATION',
  TREE_MODEL_EVALUATION = 'TREE_MODEL_EVALUATION',
}

export interface JobDependency {
  source: string;
}
export interface Job {
  name: string;
  job_type: JobType;
  is_federated: boolean;
  is_left?: boolean;
  is_manual?: boolean;
  variables: Variable[];
  dependencies: JobDependency[];
  yaml_template?: string;
}

export enum PodState {
  RUNNING = 'Running',
  COMPLETED = 'Succeeded',
  FAILED = 'Failed',
  PENDING = 'Pending',
  UNKNOWN = 'Unknown',
  FL_SUCCEED = 'Flapp_succeeded', // completed and has freed resources
  FL_FAILED = 'Flapp_failed', // failed and freed has free resources
}

export interface Pod {
  name: string;
  status: PodState;
  pod_type: string;
  conditions?: {
    message: string;
  }[];
}

export interface JobExecutionDetalis {
  id: number;
  name: string;
  state: JobState;
  job_type: JobType;
  workflow_id: number;
  project_id: number;
  pods: Pod[]; // workers details
  created_at: number;
  updated_at: number;
  deleted_at: number;
  completed_at?: number;
  yaml_template?: string;
}
