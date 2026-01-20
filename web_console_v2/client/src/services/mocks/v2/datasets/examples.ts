import {
  Dataset,
  DatasetDataType,
  DatasetKindBackEndType,
  DatasetStateFront,
  DatasetTransactionStatus,
  DatasetType__archived,
  DatasetRawPublishStatus,
  DatasetProcessedAuthStatus,
  DatasetProcessedMyAuthStatus,
  DatasetJobListItem,
  DataJobBackEndType,
  DatasetJobState,
} from 'typings/dataset';

const sharedTimes = {
  created_at: 1611205103,
  updated_at: 1611305103,
};

export const unfinishedImporting: Dataset = {
  id: 1,
  uuid: 1,
  project_id: 1,
  num_feature: 1,
  num_example: 1,
  name: 'Mocked Dataset with a looooooooooog name',
  dataset_type: DatasetType__archived.STREAMING,
  comment: 'comment here',
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.FAILED,
  dataset_format: DatasetDataType.STRUCT,
  schema_errors: {
    check_state: 'schema check failed',
    files: [],
    check_error: 'schema json file format is invalid.',
  },
  validation_jsonschema: {
    title: 'Test Matrix',
    description: 'The structure of a line',
    type: 'object',
    properties: {
      raw_id: {
        description: 'raw id',
        type: 'string',
      },
      z_1: {
        description: 'dimension 1',
        type: 'number',
      },
      z_2: {
        description: 'dimension 2',
        type: 'number',
        exclusiveMinimum: 0,
      },
      z_3: {
        description: 'dimension 3',
        type: 'number',
        exclusiveMaximum: 100,
      },
      z_4: {
        description: 'dimension 4',
        type: 'number',
      },
      event_time: {
        description: 'time',
        type: 'number',
      },
    },
    required: ['raw_id', 'z_1', 'z_2', 'z_3', 'x_3'],
  },
  file_size: 1024,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};

export const importFailed: Dataset = {
  id: 2,
  uuid: 2,
  project_id: 2,
  num_feature: 2,
  num_example: 2,
  name: 'Failed one',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.FAILED,
  dataset_format: DatasetDataType.STRUCT,
  file_size: 2048,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};

export const successfullyImport: Dataset = {
  id: 3,
  uuid: 3,
  project_id: 1,
  num_feature: 100,
  num_example: 2,
  name: 'Import succeeded',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.PROCESSING,
  dataset_format: DatasetDataType.STRUCT,
  file_size: 12345,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};

export const datasetStateFrontFailed: Dataset = {
  id: 4,
  uuid: 4,
  project_id: 1,
  num_feature: 100,
  num_example: 2,
  name: 'Import succeeded',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.FAILED,
  dataset_format: DatasetDataType.PICTURE,
  file_size: 9527,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};

export const datasetStateFrontSuccess: Dataset = {
  id: 4,
  uuid: 4,
  project_id: 1,
  num_feature: 100,
  num_example: 2,
  name: 'Import succeeded',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.SUCCEEDED,
  dataset_format: DatasetDataType.PICTURE,
  file_size: 9527,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};

export const datasetStateFrontPending: Dataset = {
  id: 4,
  uuid: 4,
  project_id: 1,
  num_feature: 100,
  num_example: 2,
  name: 'Import succeeded',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.PENDING,
  dataset_format: DatasetDataType.PICTURE,
  file_size: 9527,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};

export const datasetStateFrontProcess: Dataset = {
  id: 4,
  uuid: 4,
  project_id: 1,
  num_feature: 100,
  num_example: 2,
  name: 'Import succeeded',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.PROCESSING,
  dataset_format: DatasetDataType.PICTURE,
  file_size: 9527,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};

export const datasetStateFrontDelete: Dataset = {
  id: 4,
  uuid: 4,
  project_id: 1,
  num_feature: 100,
  num_example: 2,
  name: 'Import succeeded',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.DELETING,
  dataset_format: DatasetDataType.PICTURE,
  file_size: 9527,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};

export const importFailedWithNoErrorMessage: Dataset = {
  id: 5,
  uuid: 5,
  project_id: 2,
  num_feature: 2,
  num_example: 2,
  name: 'Failed one',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.FAILED,
  dataset_format: DatasetDataType.STRUCT,
  file_size: 111222333,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};

export const deleting: Dataset = {
  id: 6,
  uuid: 6,
  project_id: 2,
  num_feature: 2,
  num_example: 2,
  name: 'Deleting',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.DELETING,
  dataset_format: DatasetDataType.STRUCT,
  file_size: 223344,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};
export const deleteFailed: Dataset = {
  id: 7,
  uuid: 7,
  project_id: 2,
  num_feature: 2,
  num_example: 2,
  name: 'Deleting fail',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.FAILED,
  dataset_format: DatasetDataType.STRUCT,
  file_size: 5678,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};

export const frontendSucceeded: Dataset = {
  id: 11,
  uuid: 11,
  project_id: 2,
  num_feature: 2,
  num_example: 2,
  name: 'processing succeede',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.SUCCEEDED,
  dataset_format: DatasetDataType.STRUCT,
  file_size: 5678,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};
export const frontendFailed: Dataset = {
  id: 12,
  uuid: 12,
  project_id: 2,
  num_feature: 2,
  num_example: 2,
  name: 'processing failed',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.FAILED,
  dataset_format: DatasetDataType.STRUCT,
  file_size: 5678,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};
export const frontendProcessing: Dataset = {
  id: 13,
  uuid: 13,
  project_id: 2,
  num_feature: 2,
  num_example: 2,
  name: 'processing',
  dataset_type: DatasetType__archived.PSI,
  ...sharedTimes,
  path: '/path/to/dataset',
  state_frontend: DatasetStateFront.PROCESSING,
  dataset_format: DatasetDataType.STRUCT,
  file_size: 5678,
  dataset_kind: DatasetKindBackEndType.RAW,
  publish_frontend_state: DatasetRawPublishStatus.PUBLISHED,
  auth_frontend_state: DatasetProcessedAuthStatus.AUTH_APPROVED,
  local_auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
  participants_info: {
    participants_map: {
      my: {
        auth_status: DatasetProcessedMyAuthStatus.AUTHORIZED,
      },
    },
  },
};

export const datasetJobRunningState: DatasetJobListItem = {
  coordinator_id: 0,
  created_at: 1668050255,
  has_stages: true,
  id: 6181,
  kind: DataJobBackEndType.EXPORT,
  name: 'export-lhh-test-dataset-ot-0-2',
  project_id: 31,
  result_dataset_id: 9720,
  result_dataset_name: 'export-lhh-test-dataset-ot-0-2',
  state: DatasetJobState.RUNNING,
  uuid: 'u70fb2b1cfcb5437893c',
};

export const datasetJobSuccessState: DatasetJobListItem = {
  coordinator_id: 0,
  created_at: 1668050255,
  has_stages: true,
  id: 6181,
  kind: DataJobBackEndType.EXPORT,
  name: 'export-lhh-test-dataset-ot-0-2',
  project_id: 31,
  result_dataset_id: 9720,
  result_dataset_name: 'export-lhh-test-dataset-ot-0-2',
  state: DatasetJobState.SUCCEEDED,
  uuid: 'u70fb2b1cfcb5437893c',
};

export const datasetJobFailedState: DatasetJobListItem = {
  coordinator_id: 0,
  created_at: 1668050255,
  has_stages: true,
  id: 6181,
  kind: DataJobBackEndType.EXPORT,
  name: 'export-lhh-test-dataset-ot-0-2',
  project_id: 31,
  result_dataset_id: 9720,
  result_dataset_name: 'export-lhh-test-dataset-ot-0-2',
  state: DatasetJobState.FAILED,
  uuid: 'u70fb2b1cfcb5437893c',
};

export const datasetJobPendingState: DatasetJobListItem = {
  coordinator_id: 0,
  created_at: 1668050255,
  has_stages: true,
  id: 6181,
  kind: DataJobBackEndType.EXPORT,
  name: 'export-lhh-test-dataset-ot-0-2',
  project_id: 31,
  result_dataset_id: 9720,
  result_dataset_name: 'export-lhh-test-dataset-ot-0-2',
  state: DatasetJobState.PENDING,
  uuid: 'u70fb2b1cfcb5437893c',
};

export const datasetJobStopedState: DatasetJobListItem = {
  coordinator_id: 0,
  created_at: 1668050255,
  has_stages: true,
  id: 6181,
  kind: DataJobBackEndType.EXPORT,
  name: 'export-lhh-test-dataset-ot-0-2',
  project_id: 31,
  result_dataset_id: 9720,
  result_dataset_name: 'export-lhh-test-dataset-ot-0-2',
  state: DatasetJobState.STOPPED,
  uuid: 'u70fb2b1cfcb5437893c',
};

export const transactionFailed = DatasetTransactionStatus.FAILED;
export const transactionProcessing = DatasetTransactionStatus.PROCESSING;
export const transactionSucceeded = DatasetTransactionStatus.SUCCEEDED;
