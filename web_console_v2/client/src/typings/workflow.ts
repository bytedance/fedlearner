import { JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import { Job, JobExecutionDetalis, CreateJobFlag } from './job';
import { Variable } from './variable';
import {
  JobDefinitionForm,
  VariableDefinitionForm,
} from 'views/WorkflowTemplates/TemplateForm/stores';
import { ValueType } from './settings';

export type WorkflowConfig<J = Job, V = Variable> = {
  group_alias: string;
  variables: V[];
  job_definitions: J[];
};

export type ChartWorkflowConfig = WorkflowConfig<JobNodeRawData>;

export enum WorkflowType {
  MY = 'my',
  SYSTEM = 'system',
}

export enum WorkflowTemplateMenuType {
  MY = 'my',
  BUILT_IN = 'built-in',
  PARTICIPANT = 'participant',
}
export enum WorkflowTemplateType {
  MY = 0,
  BUILT_IN = 1,
  PARTICIPANT = 2,
}

export interface WorkflowTemplate<J = Job, V = Variable> {
  id: number;
  name: string;
  is_local?: boolean;
  group_alias: string;
  comment?: string;
  config: WorkflowConfig<J, V>;
  editor_info?: WorkflowTemplateEditInfo;
  kind: WorkflowTemplateType;
  creator_username?: string;
  created_at?: number;
  updated_at?: number;
  revision_id?: number;
}

export interface RevisionDetail<J = Job, V = Variable> {
  is_local?: boolean;
  name?: string;
  id: number;
  revision_index: number;
  comment?: string;
  template_id: string;
  config: WorkflowConfig<J, V>;
  editor_info?: WorkflowTemplateEditInfo;
}

export type RevisionPayload = {
  comment?: string;
};

export interface TemplateRevision {
  id: number;
  revision_index: number;
  comment?: string;
  template_id: string;
  created_at?: number;
}

export type WorkflowTemplatePayload<
  J = Job | JobDefinitionForm,
  V = Variable | VariableDefinitionForm
> = Omit<WorkflowTemplate<J, V>, 'id' | 'is_local' | 'kind'>;

export type WorkflowTemplateEditInfo = {
  yaml_editor_infos: {
    [jobName: string]: YamlEditorInfo;
  };
};

export type YamlEditorInfo = {
  slots: {
    [slotName: string]: JobSlot;
  };
  meta_yaml: string;
  variables?: Variable[];
};

export type JobSlot = {
  reference: string;
  reference_type: JobSlotReferenceType;
  value_type: ValueType;
  default_value: any;
  help?: string;
  label: string;
};

export enum JobSlotReferenceType {
  DEFAULT = 'DEFAULT',
  SELF = 'SELF',
  OTHER_JOB = 'OTHER_JOB',
  WORKFLOW = 'WORKFLOW',
  PROJECT = 'PROJECT',
  SYSTEM = 'SYSTEM',
  JOB_PROPERTY = 'JOB_PROPERTY',
}

export type WorkflowInitiatePayload<J = JobNodeRawData> = {
  name: string;
  project_id: ID;
  forkable: boolean;
  create_job_flags?: CreateJobFlag[];
  cron_config?: string;
  config: WorkflowConfig<J>;
  comment?: string;
  local_extra?: string;
  extra?: string;
  template_id?: ID | null;
  template_revision_id?: ID | null;
};

export type WorkflowAcceptPayload<J = JobNodeRawData> = {
  forkable: boolean;
  create_job_flags?: CreateJobFlag[];
  cron_config?: string;
  config: WorkflowConfig<J>;
  comment?: string;
  template_id?: ID | null;
  template_revision_id?: ID | null;
};

export type WorkflowForkPayload = WorkflowInitiatePayload & {
  forked_from: ID;
  is_local?: boolean;
  cron_config?: string;
  create_job_flags: CreateJobFlag[]; // e.g. [raw_data, training...]
  peer_create_job_flags: CreateJobFlag[];
  fork_proposal_config: ChartWorkflowConfig;
};

export enum WorkflowState {
  UNKNOWN = 'UNKNOWN',
  INVALID = 'INVALID',
  RUNNING = 'RUNNING',
  STOPPED = 'STOPPED',
  FAILED = 'FAILED',
  COMPLETED = 'COMPLETED',
  PREPARE_RUN = 'PREPARE_RUN',
  PREPARE_STOP = 'PREPARE_STOP',
  WARMUP_UNDERHOOD = 'WARMUP_UNDERHOOD',
  PENDING_ACCEPT = 'PENDING_ACCEPT',
  READY_TO_RUN = 'READY_TO_RUN',
  PARTICIPANT_CONFIGURING = 'PARTICIPANT_CONFIGURING',
}

export enum WorkflowStateFilterParam {
  UNKNOWN = 'unknown',
  INVALID = 'invalid',
  RUNNING = 'running',
  STOPPED = 'stopped',
  FAILED = 'failed',
  COMPLETED = 'completed',
  PREPARE_RUN = 'prepare_run',
  PREPARE_STOP = 'prepare_stop',
  WARMUP_UNDERHOOD = 'warmup',
  PENDING_ACCEPT = 'pending',
  READY_TO_RUN = 'ready',
  PARTICIPANT_CONFIGURING = 'configuring',
}

export type WorkflowStateType = `${WorkflowState}`;
export type WorkflowStateFilterParamType = `${WorkflowStateFilterParam}`;

type TemplateInfo = {
  id: number;
  name?: string | null;
  revision_index?: number;
  is_modified: boolean;
};

export type Workflow = {
  id: number;
  uuid?: string;
  name: string;
  project_id: ID;
  config: WorkflowConfig | null;
  is_local?: boolean;
  forkable: boolean;
  favour: boolean;
  metric_is_public?: boolean;
  forked_from?: number;
  comment: string | null;
  state: WorkflowState;
  created_at: DateTime;
  updated_at: DateTime;
  cron_config?: string;
  start_at?: DateTime | null;
  stop_at?: DateTime | null;
  template_info?: TemplateInfo;
  editor_info?: WorkflowTemplateEditInfo;
  creator?: string;

  extra?: any;
  local_extra?: any;

  'model.name'?: string;
  'model.desc'?: string;
  'model.dataset_id'?: any;
  'model.creator'?: any;
  'model.group_id'?: any;
  'model.parent_job_name'?: string;
  'model_group.name'?: string;
  'model_group.desc'?: string;
  'model.algorithm_type'?: string;
  is_allow_coordinator_parameter_tuning?: boolean;
  is_share_model_evaluation_index?: boolean;
  isReceiver?: boolean;
  /** created from model-center module(model train) */
  isTrainMode?: boolean;
  /** created from model-center module(model offline pediction) */
  isPredictionMode?: boolean;
  /** created from model-center module(model evaluation) */
  isEvaluationMode?: boolean;

  'prediction.name'?: string;
  'prediction.desc'?: string;
  'prediction.dataset_id'?: string;

  'evaluation.name'?: string;
  'evaluation.desc'?: string;
  'evaluation.dataset_id'?: string;
};

export type WorkflowExecutionDetails = {
  uuid: string;
  jobs: JobExecutionDetalis[];
  run_time: number;
  create_job_flags?: CreateJobFlag[];
  peer_create_job_flags?: CreateJobFlag[];
} & Workflow;

export enum Tag {
  RESOURCE_ALLOCATION = 'RESOURCE_ALLOCATION', // 资源配置
  INPUT_PARAM = 'INPUT_PARAM', // 输入参数
  INPUT_PATH = 'INPUT_PATH', // 输入路径
  OUTPUT_PATH = 'OUTPUT_PATH', // 输出路径
  OPERATING_PARAM = 'OPERATING_PARAM', // 运行参数
  SYSTEM_PARAM = 'SYSTEM_PARAM', // 系统变量
}
