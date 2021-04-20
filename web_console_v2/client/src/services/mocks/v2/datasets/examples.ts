import { BatchState, DataBatch, DataFile, Dataset, DatasetType, FileState } from 'typings/dataset';

const sharedTimes = {
  created_at: 1611205103,
  updated_at: 1611305103,
};

const dataFile: DataFile = {
  state: FileState.COMPLETED,
  size: 1024,
  source_path: '/path/to/file.data',
  destination_path: '/path/to/dest/file.data',
  error_message: 'Failed due to disk space is full',
};

const dataBatchImporting: DataBatch = {
  id: 1,
  move: false,
  event_time: 1611305203,
  dataset_id: 1,
  state: BatchState.IMPORTING,
  file_size: 10000,
  details: { files: [dataFile] },
  num_imported_file: 2,
  num_file: 10,
  ...sharedTimes,
};
const dataBatchImported: DataBatch = {
  id: 2,
  event_time: 1611305203,
  dataset_id: 1,
  state: BatchState.SUCCESS,
  file_size: 12345,
  details: { files: [dataFile] },
  move: false,
  num_imported_file: 5,
  num_file: 5,
  ...sharedTimes,
};
const dataBatchFailed: DataBatch = {
  event_time: 1611305203,
  id: 3,
  dataset_id: 1,
  state: BatchState.FAILED,
  details: { files: [dataFile] },
  move: false,
  file_size: 54321,
  num_imported_file: 1,
  num_file: 19,
  ...sharedTimes,
};

export const unfinishedImporting: Dataset = {
  id: 1,
  project_id: 1,
  name: 'Mocked Dataset with a looooooooooog name',
  dataset_type: DatasetType.STREAMING,
  comment: 'comment here',
  ...sharedTimes,
  path: '/path/to/dataset',
  data_batches: [dataBatchImporting, dataBatchImported],
};

export const importFailed: Dataset = {
  id: 2,
  project_id: 2,
  name: 'Failed one',
  dataset_type: DatasetType.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  data_batches: [dataBatchImported, dataBatchFailed],
};

export const successfullyImport: Dataset = {
  id: 3,
  project_id: 1,
  name: 'Import succeeded',
  dataset_type: DatasetType.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  data_batches: [dataBatchImported],
};
