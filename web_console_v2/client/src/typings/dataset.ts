import { Variable } from './variable';
import { WorkflowState } from './workflow';

export enum DatasetType__archived {
  PSI = 'PSI',
  STREAMING = 'STREAMING',
}

export enum DatasetDataType {
  STRUCT = 'TABULAR',
  PICTURE = 'IMAGE',
  NONE_STRUCTURED = 'NONE_STRUCTURED',
}

export enum DatasetDataTypeText {
  STRUCT = '结构化数据',
  PICTURE = '图片',
  NONE_STRUCTURED = '非结构化数据',
}

export enum DatasetStateFront {
  PROCESSING = 'PROCESSING',
  DELETING = 'DELETING',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
  PENDING = 'PENDING',
}
export enum DatasetJobState {
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
  STOPPED = 'STOPPED',
}

export enum BatchState {
  NEW = 'NEW',
  SUCCESS = 'SUCCESS',
  FAILED = 'FAILED',
  IMPORTING = 'IMPORTING',
}

export enum FileState {
  UNSPECIFIED = 'UNSPECIFIED',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
}
export enum DataJobType {
  JOIN = 'join',
  ALIGNMENT = 'alignment',
}
export enum DataJobBackEndType {
  RSA_PSI_DATA_JOIN = 'RSA_PSI_DATA_JOIN',
  LIGHT_CLIENT_RSA_PSI_DATA_JOIN = 'LIGHT_CLIENT_RSA_PSI_DATA_JOIN',
  LIGHT_CLIENT_OT_PSI_DATA_JOIN = 'LIGHT_CLIENT_OT_PSI_DATA_JOIN',
  OT_PSI_DATA_JOIN = 'OT_PSI_DATA_JOIN',
  DATA_JOIN = 'DATA_JOIN',
  DATA_ALIGNMENT = 'DATA_ALIGNMENT',
  IMPORT_SOURCE = 'IMPORT_SOURCE',
  EXPORT = 'EXPORT',
  HASH_DATA_JOIN = 'HASH_DATA_JOIN',
  ANALYZER = 'ANALYZER',
}

export enum DatasetJobType {
  JOIN = 'JOIN',
  ALIGNMENT = 'ALIGNMENT',
  IMPORT = 'IMPORT',
  EXPORT = 'EXPORT',
  ANALYZER = 'ANALYZER',
}

export enum DataJoinType {
  NORMAL = 'normal',
  PSI = 'psi',
  LIGHT_CLIENT = 'light_client',
  LIGHT_CLIENT_OT_PSI_DATA_JOIN = 'light_client_ot_psi_data_join',
  OT_PSI_DATA_JOIN = 'ot_psi_data_join',
  HASH_DATA_JOIN = 'hash_data_join',
}

export enum DataJoinToolTipText {
  PSI = 'RSA-PSI是基于RSA盲签名的PSI方式，主要通过一对公钥和私钥以及RSA算法对样本进行加密以及对齐。 RSA-PSI对服务端性能要求较高，对客户端性能要求较低，且适用于数据量较小的情况。',
  OT_PSI_DATA_JOIN = 'OT-PSI是基于不经意传输的PSI方式。OT-PSI具有求交效率高的优点，在数据量较大的情况下（比如>5000w），推荐使用OT方法进行求交，但同时其对内存、性能要求较高。',
  HASH_DATA_JOIN = '哈希求交是通过借助公共hash函数，对hash结果进行比对来实现。当样本为保密级别较低的数据时，推荐使用该方式。',
}

export type FileToImport = {
  path: string;
  size: number;
  mtime: DateTime;
};

export enum DatasetKind {
  RAW = 0,
  PROCESSED = 1,
}

export enum DatasetKindLabel {
  RAW = 'raw',
  PROCESSED = 'processed',
}

export enum DatasetKindV2 {
  RAW = 'raw',
  PROCESSED = 'processed',
  SOURCE = 'source',
  EXPORTED = 'exported',
}

export const DatasetKindLabelCapitalMapper = {
  [DatasetKindLabel.RAW]: 'RAW',
  [DatasetKindLabel.PROCESSED]: 'PROCESSED',
};

export enum DatasetKindBackEndType {
  RAW = 'RAW',
  PROCESSED = 'PROCESSED',
  INTERNAL_PROCESSED = 'INTERNAL_PROCESSED',
  SOURCE = 'SOURCE',
  EXPORTED = 'EXPORTED',
}

export enum DatasetTabType {
  MY = 'my',
  PARTICIPANT = 'participant',
}

export interface FileTreeNode {
  filename: string;
  path: string;
  /** File size */
  size: number;
  /** Last Time Modified */
  mtime: number;
  is_directory: boolean;
  files: FileTreeNode[];
}

export enum DataSourceType {
  /** local update datasource */
  LOCAL = 'local',
  /** hdfs datasource path, e.g. hdfs:///home/xxx */
  HDFS = 'hdfs',
  /** file datasource path, e.g. file:///data/xxx */
  FILE = 'file',
}

export enum DataSourceDataType {
  STRUCT = 'TABULAR',
  NONE_STRUCTURED = 'NONE_STRUCTURED',
  PICTURE = 'IMAGE',
}

export enum DataSourceDataTypeText {
  STRUCT = '结构化数据',
  UNSTRUCT = '非结构化数据',
  PICTURE = '图片',
}

export enum DataSourceStructDataType {
  CSV = 'CSV',
  TFRECORDS = 'TFRECORDS',
}
//
export enum DatasetType {
  PSI = 'PSI',
  STREAMING = 'STREAMING',
}

export type DataFile = {
  state: FileState;
  source_path: string;
  destination_path: string;
  error_message?: string | null;
} & Pick<FileToImport, 'size'>;

export type DataBatch = {
  id: number;
  event_time: DateTime;
  dataset_id: number;
  path?: string;
  state: BatchState;
  // Serialized proto of DatasetBatch
  details: {
    files: DataFile[];
  };
  file_size: number;
  num_imported_file: number;
  num_file: number;
  comment?: string | null;
  created_at: DateTime;
  updated_at: DateTime;
  deleted_at?: DateTime;
  files?: DataFile[];
};

export type DataBatchV2 = {
  id: ID;
  name: string;
  dataset_id: number;
  path?: string;
  file_size: number;
  num_example: number;
  comment?: string | null;
  created_at: DateTime;
  updated_at: DateTime;
  state: DatasetStateFront;
  latest_parent_dataset_job_stage_id: ID;
  latest_analyzer_dataset_job_stage_id: ID;
  has_stages: boolean;
};

export enum BatchAnalyzerState {
  PROCESSING = 'PROCESSING',
  DELETING = 'DELETING',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
}

export type Dataset = {
  id: ID;
  uuid: ID;
  project_id: ID;
  name: string;
  dataset_type: DatasetType__archived;
  data_source?: string;
  comment?: string;
  created_at: DateTime;
  updated_at: DateTime;
  deleted_at?: DateTime | null;
  num_feature?: number;
  num_example: number;
  path: string;
  state_frontend: DatasetStateFront;
  dataset_format: DatasetDataType;
  dataset_kind: DatasetKindBackEndType;
  validation_jsonschema?: object;
  schema_errors?: {
    check_state: string;
    check_error: string;
    files: any[];
  };
  parent_dataset_job_id?: ID;
  /** File size, byte */
  file_size: number;
  is_published?: boolean;
  /** Credits price */
  value?: number;
  need_publish?: boolean;
  schema_checkers?: DATASET_SCHEMA_CHECKER[];
  store_format?: DataSourceStructDataType;
  import_type?: DATASET_COPY_CHECKER;
  analyzer_dataset_job_id?: ID;
  publish_frontend_state: DatasetRawPublishStatus;
  auth_frontend_state: DatasetProcessedAuthStatus;
  local_auth_status: DatasetProcessedMyAuthStatus;
  participants_info: {
    participants_map: {
      [key in string]: {
        auth_status: DatasetProcessedMyAuthStatus;
      };
    };
  };
};

export type ParticipantInfo = {
  name: string;
  auth_status: DatasetProcessedMyAuthStatus;
};

export enum DatasetRawPublishStatus {
  UNPUBLISHED = 'UNPUBLISHED',
  TICKET_PENDING = 'TICKET_PENDING',
  TICKET_DECLINED = 'TICKET_DECLINED',
  PUBLISHED = 'PUBLISHED',
}

export enum DatasetProcessedAuthStatus {
  TICKET_PENDING = 'TICKET_PENDING',
  TICKET_DECLINED = 'TICKET_DECLINED',
  AUTH_PENDING = 'AUTH_PENDING',
  AUTH_APPROVED = 'AUTH_APPROVED',
}

export enum DatasetProcessedMyAuthStatus {
  PENDING = 'PENDING',
  AUTHORIZED = 'AUTHORIZED',
  WITHDRAW = 'WITHDRAW',
}

export type ParticipantDataset = {
  /** File size, byte */
  file_size: number;
  format: DatasetDataType;
  name: string;
  participant_id: ID;
  project_id: ID;
  updated_at: DateTime;
  uuid: ID;
  dataset_kind?: DatasetKindBackEndType;
  value?: number;
};

export type IntersectionDataset = {
  id: ID;
  name: string;
  comment?: string;
  status: WorkflowState | `${WorkflowState}`;
  kind: DatasetKind;
  workflow_id: ID;
  project_id: ID;
  dataset_id: ID;
  dataset_name: string;
  job_name: string;
  peer_name: string;
  num_feature?: number;
  num_example?: number;
  raw_dataset_num_example?: number;
  sample_filesize?: number;
  feature_num?: number;
  created_at: DateTime;
  updated_at: DateTime;
  deleted_at?: DateTime | null;
  path: string;
  data_source: string;
  /** File size, byte */
  file_size: number;
};

export type DatasetCreatePayload = Pick<
  Dataset,
  | 'name'
  | 'dataset_type'
  | 'comment'
  | 'project_id'
  | 'is_published'
  | 'value'
  | 'need_publish'
  | 'schema_checkers'
  | 'is_published'
> & {
  time_range?: {
    days?: number;
    hours?: number;
  };
};

export type DataBatchImportPayload = {
  need_schema_check?: boolean;
  json_schema?: string;
  data_source_id?: ID;
};

export type DatasetEditDisplay = Pick<Dataset, 'name' | 'comment'>;
export type DatasetEditPayload = Pick<DatasetEditDisplay, 'comment'>;

export type PreviewDataSample = (number | string)[];

export type PreviewDataMetric = {
  count: string;
  mean: string;
  stddev: string;
  min: string;
  max: string;
  missing_count: string;
};

export type ImageDetail = {
  annotation: { caption?: string; label: string };
  created_at: string;
  file_name?: string;
  height: number;
  name: string;
  path: string;
  width: number;
  /** FE custom field, `/api/v2/image?name=${path}` */
  uri: string;
};

export type ValueType = 'bigint' | 'float' | 'string' | 'int' | 'double';

export type PreviewData = {
  dtypes?: {
    key: string;
    value: ValueType;
  }[];
  count?: number;
  sample?: PreviewDataSample[];
  metrics?: {
    [key: string]: PreviewDataMetric;
  };
  images?: ImageDetail[];
};

export type FeatureMetric = {
  name: string;
  metrics: { [key: string]: string };
  hist: { x: number[]; y: number[] };
};

export enum ExportStatus {
  INIT = 'INIT',
  RUNNING = 'RUNNING',
  DONE = 'DONE',
  FAILED = 'FAILED',
}

export type ExportInfo = {
  status: ExportStatus;
  start_time: DateTime;
  end_time: DateTime | null;
  export_path: string;
  dataset_id: ID;
};

export type DataSource = {
  id: ID;
  uuid: string;
  project_id: ID;
  name: string;
  comment?: string;
  type: string;
  url: string;
  created_at: DateTime;
  is_user_upload?: boolean;
  dataset_format: `${DataSourceDataType}`;
  store_format: `${DataSourceStructDataType}`;
  dataset_type: `${DatasetType}`;
};

export type DataSourceCreatePayload = {
  project_id: ID;
  data_source: {
    name: string;
    data_source_url: string;
    data_source_type?: DataSourceType;
    is_user_upload?: boolean;
    dataset_format?: DataSourceDataType;
    store_format?: DataSourceStructDataType;
    dataset_type?: DatasetType;
  };
};
export type ProcessedDatasetCreatePayload = {
  dataset_job_parameter: {
    dataset_job_kind: DataJobBackEndType;
    global_configs: {
      [domainName: string]: {
        dataset_uuid: ID;
        variables: DataJobVariable[];
      };
    };
  };
  processed_dataset: {
    name: string;
    comment: string;
  };
};

export type DatasetJobCreatePayload = {
  dataset_job_parameter: {
    dataset_job_kind: DataJobBackEndType;
    global_configs: {
      [domainName: string]: {
        dataset_uuid: ID;
        variables: DataJobVariable[];
      };
    };
  };
  output_dataset_id: ID;
  time_range?: {
    days?: number;
    hours?: number;
  };
};

export type DataSourceEditPayload = DataSourceCreatePayload;

export type DataSourceCheckConnectionPayload = {
  data_source_url: string;
  file_num?: number;
  dataset_type?: DatasetType;
};

export type DataJobVariable = Omit<Variable, 'widget_schema'> & {
  widget_schema: string;
};

export type GlobalConfigs = {
  [domainName: string]: {
    dataset_uuid: string;
    variables: DataJobVariable[];
  };
};

export type DatasetJob = {
  global_configs: {
    global_configs: GlobalConfigs;
  };
  kind: DataJobBackEndType;
  project_id: ID;
  result_dataset_name: string;
  result_dataset_uuid: string;
  uuid: string;
  workflow_id: string;
  input_data_batch_num_example: number;
  output_data_batch_num_example: number;
  state: DatasetJobState;
  coordinator_id: ID;
  created_at: DateTime;
  creator_username: string;
  finished_at: DateTime;
  updated_at: DateTime;
  started_at: DateTime;
  name: string;
  has_stages: boolean;
  scheduler_state: DatasetJobSchedulerState;
  time_range?: {
    days?: number;
    hours?: number;
  };
  scheduler_message?: string;
};

export enum DatasetJobSchedulerState {
  PENDING = 'PENDING',
  RUNNABLE = 'RUNNABLE',
  STOPPED = 'STOPPED',
}

export type DatasetJobStage = {
  id: ID;
  name: string;
  dataset_job_id: ID;
  data_batch_id: ID;
  state: DatasetJobState;
  created_at: DateTime;
  started_at: DateTime;
  finished_at: DateTime;
  kind: DataJobBackEndType;
  output_data_batch_id: ID;
  input_data_batch_num_example: number;
  output_data_batch_num_example: number;
  workflow_id: ID;
  global_configs: {
    global_configs: GlobalConfigs;
  };
};

export type DatasetJobListItem = {
  name: string;
  uuid: string;
  project_id: ID;
  result_dataset_id: ID;
  result_dataset_name: string;
  state: DatasetJobState;
  kind: DataJobBackEndType;
  created_at: DateTime;
  id?: ID;
  coordinator_id?: ID;
  has_stages: boolean;
};

export type DatasetJobStop = {
  code: number;
  data?: {
    id?: ID;
    input_data_batch_num_example?: string;
    output_data_batch_num_example?: string;
    workflow_id?: ID;
    coordinator_id?: ID;
    created_at?: DateTime;
    updated_at?: DateTime;
    kind?: string;
    state?: string;
    finished_at?: DateTime;
    global_configs?: any;
    message?: string;
  };
};

export enum DatasetTransactionStatus {
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
  PROCESSING = 'PROCESSING',
}

export type TransactionExtraData = {
  transaction_info: string;
  dataset_uuid: ID;
};

export type DatasetTransactionItem = {
  trans_hash: string;
  block_number: number;
  trans_index: number;
  sender_name: string;
  receiver_name: string;
  value: number;
  extra_data: TransactionExtraData;
  timestamp: number;
  status: DatasetTransactionStatus;
};

export type DatasetLedger = {
  total_value: number;
  transactions: DatasetTransactionItem[];
};

export type ExportDataset = {
  dataset_job_id: ID;
  export_dataset_id: ID;
};

export enum DatasetForceState {
  RUNNING = 'RUNNING',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
}

export enum DATASET_SCHEMA_CHECKER {
  RAW_ID_CHECKER = 'RAW_ID_CHECKER',
  NUMERIC_COLUMNS_CHECKER = 'NUMERIC_COLUMNS_CHECKER',
}

export enum DATASET_COPY_CHECKER {
  COPY = 'COPY',
  NONE_COPY = 'NO_COPY',
}
