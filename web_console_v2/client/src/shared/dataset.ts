import { StateTypes } from 'components/StateIndicator';
import i18n from 'i18n';
import { memoize } from 'lodash';
import { BatchState, Dataset } from 'typings/dataset';

// --------- State judgement ------------

export function isImportSuccess(data: Dataset) {
  return data.data_batches.every((item) => item.state === BatchState.SUCCESS);
}

export function isAvailable(data: Dataset) {
  // TODO: how to determinte that the dataset is available?
  return isImportSuccess(data);
}

export function isImportFailed(data: Dataset) {
  return data.data_batches.some((item) => item.state === BatchState.FAILED);
}

export function isImporting(data: Dataset) {
  return data.data_batches.some((item) => item.state === BatchState.IMPORTING);
}

export function hasAppendingDataBatch(data: Dataset) {
  return false;
}

// --------- Helpers ------------

export function getTotalDataSize(data: Dataset) {
  return _sumUp(data, 'file_size');
}

export const getImportedProportion = memoize((data: Dataset) => {
  const total = _sumUp(data, 'num_file');
  const imported = _sumUp(data, 'num_imported_file');
  return {
    total,
    imported,
  };
});

export function getImportStage(data: Dataset): { type: StateTypes; text: string; tip?: string } {
  if (isImporting(data)) {
    return {
      type: 'processing',
      text: i18n.t('dataset.state_importing', getImportedProportion(data)),
    };
  }

  if (isImportSuccess(data)) {
    return {
      type: 'success',
      text: i18n.t('dataset.state_available'),
    };
  }

  if (isImportFailed(data)) {
    return {
      type: 'error',
      text: i18n.t('dataset.state_error'),
      tip:
        data.data_batches
          .find((item) => item.state === BatchState.FAILED)!
          .details.files.find((item) => item.error_message)?.error_message || '',
    };
  }

  /* istanbul ignore next */
  return {
    text: i18n.t('dataset.state_unknown'),
    type: 'default',
  } as never;
}

// -------- Private helpers ------

function _sumUp(data: Dataset, key: 'num_file' | 'num_imported_file' | 'file_size') {
  return data.data_batches.reduce((result, current) => {
    return result + current[key];
  }, 0);
}
