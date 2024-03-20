import { Variable } from './variable';

export enum JobState {
  INVALID = 'INVALID',
  NEW = 'NEW',
  WAITING = 'WAITING',
  /** @deprecated RUNNING changes to STARTED*/
  RUNNING = 'RUNNING',
  STARTED = 'STARTED',
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

// Job definition
export interface Job {
  name: string;
  job_type: JobType;
  is_federated: boolean;
  variables: Variable[];
  dependencies: JobDependency[];
  yaml_template?: string;
}

export type JobDefinitionForm = Omit<Job, 'dependencies'>;

export enum PodState {
  RUNNING = 'RUNNING',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
  PENDING = 'PENDING',
  UNKNOWN = 'UNKNOWN',
  SUCCEEDED_AND_FREED = 'SUCCEEDED_AND_FREED', // completed and has freed resources
  FAILED_AND_FREED = 'FAILED_AND_FREED', // failed and freed has free resources

  /**
   * Deprecated state values
   */
  RUNNING__deprecated = 'running',
  SUCCEEDED__deprecated = 'succeeded',
  FAILED__deprecated = 'failed',
  PENDING__deprecated = 'pending',
  UNKNOWN__deprecated = 'Unknown',
  SUCCEEDED_AND_FREED__deprecated = 'Flapp_succeeded',
  FAILED_AND_FREED__deprecated = 'Flapp_failed',
}

export interface Pod {
  name: string;
  pod_ip: string;
  state: PodState;
  /** @deprecated */
  status?: PodState;
  pod_type: string;
  message?: string;
}

export enum CreateJobFlag {
  INVALID = 0,
  NEW = 1,
  REUSE = 2,
  DISABLED = 3,
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
  error_message?: string;
  completed_at?: number;
  yaml_template?: string;
}
