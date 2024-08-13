import { DateTimeInfo } from 'typings/app';
import { Workflow, WorkflowConfig, WorkflowState } from 'typings/workflow';
import { JobExecutionDetalis } from 'typings/job';
import { EnumAlgorithmProjectType } from './algorithm';
import { Variable, VariableWidgetSchema } from './variable';

export enum ModelManagementTabType {
  SET = 'model-set',
  FAVOURITE = 'model-favourit',
}
export enum ModelEvaluationTabType {
  EVALUATION = 'evaluation',
  COMPARE = 'compare',
}

export enum AlgorithmManagementTabType {
  MY = 'my',
  BUILT_IN = 'built-in',
  PARTICIPANT = 'participant',
}

export enum AlgorithmDetailTabType {
  PREVIEW = 'preview',
  CHANGE_LOG = 'change-log',
}

export enum ResourceTemplateType {
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  CUSTOM = 'custom',
}

export enum FederationType {
  CROSS_SAMPLE = 'cross_sample',
  CROSS_FEATURE = 'cross_feature',
}
export enum UploadType {
  PATH = 'path',
  LOCAL = 'local',
}

export enum LossType {
  LOGISTIC = 'logistic',
  MSE = 'mse',
}

export enum AlgorithmType {
  TREE = 'tree',
  NN = 'nn',
}

export enum FederalType {
  VERTICAL = 'vertical',
  HORIZONTAL = 'horizontal',
}

export enum Role {
  LEADER = 'leader',
  FOLLOWER = 'follower',
}
export enum RoleUppercase {
  LEADER = 'Leader',
  FOLLOWER = 'Follower',
}
export enum TrainRoleType {
  LABEL = RoleUppercase.LEADER,
  FEATURE = RoleUppercase.FOLLOWER,
}

export { WorkflowState as ModelJobState };

export enum ModelJobRole {
  COORDINATOR = 'COORDINATOR',
  PARTICIPANT = 'PARTICIPANT',
}

export type ModelJobType =
  | 'UNSPECIFIED'
  | 'NN_TRAINING'
  | 'TREE_TRAINING'
  | 'NN_EVALUATION'
  | 'TREE_EVALUATION'
  | 'NN_PREDICTION'
  | 'TREE_PREDICTION'
  | 'TRAINING'
  | 'EVALUATION'
  | 'PREDICTION';

export type ModelSet = {
  id: number;
  name: string;
  comment: string | null;
  created_at: DateTime;
  updated_at: DateTime;
  deleted_at: DateTime;
  extra: any;

  algorithm?: string;
  version?: string;
  creator?: string;
  project_id?: string;
  isCompareReport?: boolean;
  selectedModelIdList?: string[];
};

export type ModelSetCreatePayload = {
  name: string;
  project_id: ID;
  comment?: string;
  extra?: any;
};
export type ModelSetUpdatePayload = {
  comment?: string;
  extra?: any;
};

export type ModelJobGroup = {
  id: ID;
  uuid: ID;
  project_id: ID;
  name: string;
  comment: string | null;
  role: ModelJobRole | `${ModelJobRole}`;
  authorized: boolean;
  intersection_dataset_id: ID;
  dataset_id: ID;
  algorithm_type: EnumAlgorithmProjectType | `${EnumAlgorithmProjectType}`;
  algorithm_project_id: ID;
  algorithm_id: ID;
  configured: boolean;
  config?: WorkflowConfig;
  latest_job_state: ModelJobStatus;
  latest_version: number;
  model_jobs?: ModelJob[];
  creator_username: string;
  coordinator_id?: ID;
  auth_frontend_status?: ModelGroupStatus;
  participants_info?: { participants_map: Record<string, any> };
  auto_update_status?: AutoModelJobStatus;

  // TODO: explicit type
  extra: unknown;

  /** TODO: custom field, will be deleted soon */
  creator: string;
  cron_config: string;
  algorithm_project_uuid_list:
    | { algorithm_projects: { [pure_domain_name: string]: ID } }
    | undefined;
} & DateTimeInfo;
export type ModelJobGroupCreatePayload = {
  name: string;
  algorithm_type: EnumAlgorithmProjectType | `${EnumAlgorithmProjectType}`;
  dataset_id?: ID;
};
export type ModelJobGlobalConfig = {
  dataset_uuid?: ID;
  global_config: {
    [pure_domain_name: string]: {
      algorithm_uuid?: ID;
      //TODO：support param algorithm_project_uuid
      algorithm_project_uuid?: ID;
      algorithm_parameter?: { ['variables']: AlgorithmParams[] | undefined };
      variables: Variable[];
    };
  };
};
export type ModelJobGroupUpdatePayload = {
  authorized?: boolean;
  dataset_id?: ID;
  algorithm_id?: ID;
  config?: WorkflowConfig;
  comment?: string;
  cron_config?: string;
  global_config?: ModelJobGlobalConfig;
};
export type PeerModelJobGroupUpdatePayload = {
  config?: WorkflowConfig;
  global_config?: ModelJobGlobalConfig;
};

export type ModelJobMetrics = {
  train: {
    [key: string]:
      | [number[], number[]]
      | {
          steps: number[];
          values: number[];
        };
  };
  eval: {
    [key: string]:
      | [number[], number[]]
      | {
          steps: number[];
          values: number[];
        };
  };
  feature_importance: { [featureName: string]: number };
  confusion_matrix?: {
    /** True Postive, position: top left */
    tp: number;
    /** False Postive, position: top right */
    fp: number;
    /** False Negative, position: bottom left */
    fn: number;
    /** True Negative, position: bottom right */
    tn: number;
  };
};

export type Item = {
  label: string;
  value: number | null;
};
export type FormattedModelJobMetrics = {
  train: Item[];
  eval: Item[];
  feature_importance: Item[];
  confusion_matrix?: Array<Item & { percentValue: string }>;
  trainMaxValue: number;
  evalMaxValue: number;
  featureImportanceMaxValue: number;
};

export type ModelJobQueryParams = {
  projectId?: ID;
  types?: Array<ModelJobType>;
};

export interface ModelJobQueryParams_new {
  keyword?: string;
  project_id?: string;
  group_id?: string;
  algorithm_types?: AlgorithmType[];
  states?: WorkflowState[];
  page?: number;
  page_size?: number;
  types?: 'EVALUATION' | 'PREDICTION';
  role?: string;
  filter?: string;
}

export type ModelJob = {
  id: number;
  uuid: ID;
  name: string;
  comment: string;
  model_job_type: ModelJobType;
  model_name?: string;
  state: WorkflowState;
  status: ModelJobStatus;
  job_name: string;
  job_id: number;
  workflow_id: number;
  workflow_uuid: ID;
  /** model set id */
  group_id: number;
  project_id: number;
  code_id: number;
  dataset_id: number;
  dataset_name?: string;
  intersection_dataset_id: number;
  intersection_dataset_name?: string;
  model_id: number;
  params: any;
  algorithm_type: EnumAlgorithmProjectType;
  algorithm_id: ID;
  role: 'COORDINATOR' | 'PARTICIPANT';
  config: WorkflowConfig;
  parent?: Model;
  metrics: ModelJobMetrics;
  version: number;

  extra: any;
  local_extra: any;
  detail_level: any[];

  created_at: DateTime;
  updated_at: DateTime;
  deleted_at: DateTime;
  started_at?: DateTime;
  stopped_at?: DateTime;

  job: JobExecutionDetalis;
  workflow: Workflow;

  /** no source field */
  'model.name'?: string;
  'model.desc'?: string;
  'model.dataset_id'?: any;
  'model.group_id'?: any;
  'model.parent_job_name'?: string;

  formattedMetrics?: FormattedModelJobMetrics;

  output_models: Model[];
  creator_username: string;
  metric_is_public: boolean;
  global_config?: ModelJobGlobalConfig;
  auto_update?: boolean;
  data_batch_id?: ID;
  auth_status?: string;
};

export type ModelUpdatePayload = {
  comment?: string;
};

export type ModelType = 'UNSPECIFIED' | 'TREE_MODEL' | 'NN_MODEL';

export type Model = {
  id: number;
  uuid: string;
  name: string;
  comment: string;
  model_type: ModelType;
  model_path: string;
  // TODO: federated_type
  federated_type: string;
  version: number | null;
  favorite: boolean;
  /** Model set id */
  group_id: ID | null;
  project_id: ID | null;
  model_job_id: ID | null;
  model_job_name: string | null;
  job_id: ID | null;
  job_name: string | null;
  workflow_id: ID | null;
  workflow_name: string | null;
} & DateTimeInfo;

export type Algorithm = {
  id: number;
  name: string;
  comment: string;
  state: string;
  type: string;
  file: string;
  file_owner: string;
  file_no_owner: string;
  project_id?: ID;

  creator: string;
  created_at: DateTime;
  updated_at: DateTime;
  deleted_at: DateTime;
};

export type AlgorithmChangeLog = {
  id: number;
  comment: string;
  creator: string;
  created_at: DateTime;
  updated_at: DateTime;
  deleted_at: DateTime;
};

export type FakeAlgorithm = {
  id: number;
  name: string;
  value: string;
  comment: string;
  type: ModelType;

  created_at: DateTime;
  updated_at: DateTime;
  deleted_at: DateTime;
};

export type AlgorithmParams = {
  id?: string;
  name: string;
  display_name: string;
  required: boolean;
  comment: string;
  value: string;
};

export interface ModelJobCreateFormData {
  name: string;
  model_job_type: ModelJobType;
  algorithm_type: AlgorithmType;
  algorithm_id: string;
  eval_model_job_id?: string;
  dataset_id: string;
  config: Record<string, any>;
  comment?: string;
  model_id?: string;
}

export type ModelJobPatchFormData = Pick<
  ModelJobCreateFormData,
  'algorithm_id' | 'dataset_id' | 'config' | 'comment'
>;

export interface ModelJobGroupCreateForm {
  name: string;
  comment: string | undefined;
  dataset_id: ID;
  algorithm_type: EnumAlgorithmProjectType;
  algorithm_project_list?: { algorithmProjects: { [pure_domain_name: string]: ID } };
  loss_type?: LossType;
}
export interface ModelJobTrainCreateForm {
  name: string;
  model_job_type: ModelJobType;
  algorithm_type?: EnumAlgorithmProjectType;
  dataset_id?: string;
  comment?: string;
  global_config?: ModelJobGlobalConfig;
  group_id?: ID;
  data_batch_id?: ID;
}

export interface ModelJobDefinitionQueryParams {
  model_job_type: string;
  algorithm_type: string;
}

export interface ModelJobDefinitionResult {
  is_federated: boolean;
  variables: Variable[];
}

export type ModelJobVariable = Omit<Variable, 'widget_schema'> & {
  widget_schema: string | VariableWidgetSchema;
};
// TODO: 等后端定义
export enum ModelGroupStatus {
  TICKET_PENDING = 'TICKET_PENDING',
  TICKET_DECLINE = 'TICKET_DECLINE',
  CREATE_PENDING = 'CREATE_PENDING',
  CREATE_FAILED = 'CREATE_FAILED',
  SELF_AUTH_PENDING = 'SELF_AUTH_PENDING',
  PART_AUTH_PENDING = 'PART_AUTH_PENDING',
  ALL_AUTHORIZED = 'ALL_AUTHORIZED',
}

export enum ModelJobAuthStatus {
  TICKET_PENDING = 'TICKET_PENDING',
  TICKET_DECLINE = 'TICKET_DECLINE',
  CREATE_PENDING = 'CREATE_PENDING',
  CREATE_FAILED = 'CREATE_FAILED',
  SELF_AUTH_PENDING = 'SELF_AUTH_PENDING',
  PART_AUTH_PENDING = 'PART_AUTH_PENDING',
  ALL_AUTHORIZED = 'ALL_AUTHORIZED',
}

export enum EnumModelJobType {
  TRAINING = 'TRAINING',
  EVALUATION = 'EVALUATION',
  PREDICTION = 'PREDICTION',
}

export type TRouteParams = {
  id: string;
  step: keyof typeof CreateSteps;
  type: string;
};
export enum CreateSteps {
  coordinator = 1,
  participant = 2,
}

export enum AutoModelJobStatus {
  INITIAL = 'INITIAL',
  ACTIVE = 'ACTIVE',
  STOPPED = 'STOPPED',
}
export enum ModelJobStatus {
  PENDING = 'PENDING',
  CONFIGURED = 'CONFIGURED',
  ERROR = 'ERROR',
  RUNNING = 'RUNNING',
  STOPPED = 'STOPPED',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
  UNKNOWN = 'UNKNOWN',
}
