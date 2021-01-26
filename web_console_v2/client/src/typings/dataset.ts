export enum DatasetType {
  PSI = 'PSI',
  STREAMING = 'STREAMING',
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

export type FileToImport = {
  path: string;
  size: number;
  created_at: DateTime;
};

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
  state: BatchState;
  move: boolean;
  // Serialized proto of DatasetBatch
  details: {
    files: DataFile[];
  };
  file_size: number;
  imported_file_num: number;
  num_file: number;
  comment?: string | null;
  created_at: DateTime;
  updated_at: DateTime;
  deleted_at?: DateTime;
  files?: DataFile[];
};

export type Dataset = {
  id: number;
  name: string;
  dataset_type: DatasetType;
  comment?: string | null;
  created_at: DateTime;
  updated_at: DateTime;
  deleted_at?: DateTime;
  data_batches: DataBatch[];
};

export type DatasetCreatePayload = Pick<Dataset, 'name' | 'dataset_type' | 'comment'>;

export type DataBatchImportPayload = {
  files: FileToImport[];
} & Pick<DataBatch, 'event_time' | 'move'>;
