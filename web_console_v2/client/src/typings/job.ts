import { Variable } from './workflow';

export enum JobState {
  INVALID = 'INVALID',
  NEW = 'NEW',
  WAITING = 'WAITING',
  RUNNING = 'RUNNING',
  COMPLETE = 'COMPLETE',
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
  // the value is from the very underside so lowercase should make sense
  RUNNING = 'Running',
  COMPLETE = 'Complete',
  FAILED = 'Failed',
  PENDING = 'Pending',
  UNKNOWN = 'Unknown',
  FL_SUCCEED = 'Flapp_succeed', // completed
  FL_FAILED = 'Flapp_failed', // failed
}

export interface Pod {
  name: string;
  status: PodState;
  pod_type: string;
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
