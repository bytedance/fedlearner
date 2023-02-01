import { StateTypes } from 'components/StateIndicator';
import i18n from 'i18n';
import {
  DataJobBackEndType,
  Dataset,
  DatasetJobListItem,
  DatasetJobState,
  DatasetStateFront,
  DatasetTransactionStatus,
  IntersectionDataset,
  DatasetJobStage,
} from 'typings/dataset';

export function isFrontendPending(data: Dataset) {
  return data.state_frontend === DatasetStateFront.PENDING;
}

export function isFrontendProcessing(data: Dataset) {
  return data.state_frontend === DatasetStateFront.PROCESSING;
}
export function isFrontendDeleting(data: Dataset) {
  return data.state_frontend === DatasetStateFront.DELETING;
}
export function isFrontendSucceeded(data: Dataset) {
  return data.state_frontend === DatasetStateFront.SUCCEEDED;
}
export function isFrontendFailed(data: Dataset) {
  return data.state_frontend === DatasetStateFront.FAILED;
}

// ------- dataset job states judgement -------

export function isJobRunning(data: DatasetJobListItem | DatasetJobStage) {
  if (!data || !data.state) {
    return false;
  }
  return [DatasetJobState.PENDING, DatasetJobState.RUNNING].includes(data.state);
}

export function isJobSucceed(data: DatasetJobListItem | DatasetJobStage) {
  if (!data || !data.state) {
    return false;
  }
  return [DatasetJobState.SUCCEEDED].includes(data.state);
}

export function isJobFailed(data: DatasetJobListItem | DatasetJobStage) {
  if (!data || !data.state) {
    return false;
  }
  return [DatasetJobState.FAILED].includes(data.state);
}

export function isJobStopped(data: DatasetJobListItem | DatasetJobStage) {
  if (!data || !data.state) {
    return false;
  }
  return [DatasetJobState.STOPPED].includes(data.state);
}

// --------- Helpers ------------

export function getTotalDataSize(data: Dataset | IntersectionDataset) {
  return data.file_size || 0;
}

export function getImportStage(data: Dataset): { type: StateTypes; text: string; tip?: string } {
  if (isFrontendPending(data)) {
    return {
      type: 'processing',
      text: '待处理',
    };
  }
  if (isFrontendDeleting(data)) {
    return {
      type: 'processing',
      text: '删除中',
    };
  }
  if (isFrontendProcessing(data)) {
    return {
      type: 'processing',
      text: '处理中',
    };
  }
  if (isFrontendSucceeded(data)) {
    return {
      type: 'success',
      text: '可用',
    };
  }
  if (isFrontendFailed(data)) {
    return {
      type: 'error',
      text: '处理失败',
      tip: '',
    };
  }

  /* istanbul ignore next */
  return {
    text: i18n.t('dataset.state_unknown'),
    type: 'default',
  } as never;
}

/* istanbul ignore next */
export function getDatasetJobState(
  data: DatasetJobListItem | DatasetJobStage,
): { type: StateTypes; text: string; tip?: string } {
  let type: StateTypes = 'default';
  let text = i18n.t('dataset.state_unknown');
  if (isJobRunning(data)) {
    type = 'processing';
    text = i18n.t('dataset.state_dataset_job_running');
  }
  if (isJobSucceed(data)) {
    type = 'success';
    text = i18n.t('dataset.state_dataset_job_succeeded');
  }
  if (isJobFailed(data)) {
    type = 'error';
    text = i18n.t('dataset.state_dataset_job_failed');
  }
  if (isJobStopped(data)) {
    type = 'error';
    text = i18n.t('dataset.state_dataset_job_stopped');
  }
  return {
    type,
    text,
  };
}

/* istanbul ignore next */
export function getDatasetJobType(kind: DataJobBackEndType) {
  switch (kind) {
    case DataJobBackEndType.DATA_JOIN:
    case DataJobBackEndType.RSA_PSI_DATA_JOIN:
    case DataJobBackEndType.OT_PSI_DATA_JOIN:
    case DataJobBackEndType.LIGHT_CLIENT_RSA_PSI_DATA_JOIN:
    case DataJobBackEndType.LIGHT_CLIENT_OT_PSI_DATA_JOIN:
    case DataJobBackEndType.HASH_DATA_JOIN:
      return i18n.t('dataset.label_data_job_type_create');
    case DataJobBackEndType.DATA_ALIGNMENT:
      return i18n.t('dataset.label_data_job_type_alignment');
    case DataJobBackEndType.IMPORT_SOURCE:
      return i18n.t('dataset.label_data_job_type_import');
    case DataJobBackEndType.EXPORT:
      return i18n.t('dataset.label_data_job_type_export');
    case DataJobBackEndType.ANALYZER:
      return '探查';
    default:
      return 'unknown';
  }
}

export function getIntersectionRate(data: { input: number; output: number }) {
  let rate = 0;

  if (data.input && data.output) {
    rate = data.output / data.input;
  }

  return `${parseFloat((rate * 100).toFixed(2))}%`;
}

export function getTransactionStatus(
  status: DatasetTransactionStatus,
): { type: StateTypes; text: string } {
  switch (status) {
    case DatasetTransactionStatus.FAILED:
      return {
        type: 'error',
        text: i18n.t('dataset.state_transaction_failed'),
      };
    case DatasetTransactionStatus.PROCESSING:
      return {
        type: 'processing',
        text: i18n.t('dataset.state_transaction_processing'),
      };
    case DatasetTransactionStatus.SUCCEEDED:
      return {
        type: 'success',
        text: i18n.t('dataset.state_transaction_success'),
      };
    /* istanbul ignore next */
    default:
      return {
        type: 'default',
        text: i18n.t('dataset.state_unknown'),
      };
  }
}
