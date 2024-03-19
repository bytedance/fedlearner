import {
  getTotalDataSize,
  getImportStage,
  getIntersectionRate,
  getTransactionStatus,
  isFrontendPending,
  isFrontendSucceeded,
  isFrontendFailed,
  isFrontendProcessing,
  isFrontendDeleting,
  isJobRunning,
  isJobSucceed,
  isJobFailed,
  isJobStopped,
  getDatasetJobState,
} from './dataset';
import {
  successfullyImport,
  importFailed,
  unfinishedImporting,
  deleting,
  frontendSucceeded,
  frontendFailed,
  frontendProcessing,
  transactionFailed,
  transactionSucceeded,
  transactionProcessing,
  datasetStateFrontFailed,
  datasetStateFrontPending,
  datasetStateFrontProcess,
  datasetStateFrontSuccess,
  datasetStateFrontDelete,
  datasetJobPendingState,
  datasetJobFailedState,
  datasetJobRunningState,
  datasetJobStopedState,
  datasetJobSuccessState,
} from 'services/mocks/v2/datasets/examples';
import { DatasetStateFront } from 'typings/dataset';

describe('Datasets state', () => {
  it('state_frontend failed', () => {
    expect(isFrontendFailed(datasetStateFrontFailed)).toBe(true);
    expect(isFrontendFailed(datasetStateFrontPending)).toBe(false);
    expect(isFrontendFailed(datasetStateFrontProcess)).toBe(false);
    expect(isFrontendFailed(datasetStateFrontSuccess)).toBe(false);
    expect(isFrontendFailed(datasetStateFrontDelete)).toBe(false);
  });
  it('state_frontend success', () => {
    expect(isFrontendSucceeded(datasetStateFrontSuccess)).toBe(true);
    expect(isFrontendSucceeded(datasetStateFrontPending)).toBe(false);
    expect(isFrontendSucceeded(datasetStateFrontProcess)).toBe(false);
    expect(isFrontendSucceeded(datasetStateFrontFailed)).toBe(false);
    expect(isFrontendSucceeded(datasetStateFrontDelete)).toBe(false);
  });
  it('state_frontend pending', () => {
    expect(isFrontendPending(datasetStateFrontPending)).toBe(true);
    expect(isFrontendPending(datasetStateFrontFailed)).toBe(false);
    expect(isFrontendPending(datasetStateFrontProcess)).toBe(false);
    expect(isFrontendPending(datasetStateFrontSuccess)).toBe(false);
    expect(isFrontendPending(datasetStateFrontDelete)).toBe(false);
  });
  it('state_frontend process', () => {
    expect(isFrontendProcessing(datasetStateFrontProcess)).toBe(true);
    expect(isFrontendProcessing(datasetStateFrontPending)).toBe(false);
    expect(isFrontendProcessing(datasetStateFrontFailed)).toBe(false);
    expect(isFrontendProcessing(datasetStateFrontSuccess)).toBe(false);
    expect(isFrontendProcessing(datasetStateFrontDelete)).toBe(false);
  });
  it('state_frontend deleting', () => {
    expect(isFrontendDeleting(datasetStateFrontDelete)).toBe(true);
    expect(isFrontendDeleting(datasetStateFrontPending)).toBe(false);
    expect(isFrontendDeleting(datasetStateFrontFailed)).toBe(false);
    expect(isFrontendDeleting(datasetStateFrontSuccess)).toBe(false);
    expect(isFrontendDeleting(datasetStateFrontProcess)).toBe(false);
  });

});

describe('Datasets job state', () => {
  it('Datasets job failed', () => {
    expect(isJobFailed(datasetJobFailedState)).toBe(true);
    expect(isJobFailed(datasetJobPendingState)).toBe(false);
    expect(isJobFailed(datasetJobRunningState)).toBe(false);
    expect(isJobFailed(datasetJobStopedState)).toBe(false);
    expect(isJobFailed(datasetJobSuccessState)).toBe(false);
  });
  it('Datasets job success', () => {
    expect(isJobSucceed(datasetJobSuccessState)).toBe(true);
    expect(isJobSucceed(datasetJobPendingState)).toBe(false);
    expect(isJobSucceed(datasetJobRunningState)).toBe(false);
    expect(isJobSucceed(datasetJobStopedState)).toBe(false);
    expect(isJobSucceed(datasetJobFailedState)).toBe(false);
  });
  it('Datasets job stoped', () => {
    expect(isJobStopped(datasetJobStopedState)).toBe(true);
    expect(isJobStopped(datasetJobPendingState)).toBe(false);
    expect(isJobStopped(datasetJobRunningState)).toBe(false);
    expect(isJobStopped(datasetJobSuccessState)).toBe(false);
    expect(isJobStopped(datasetJobFailedState)).toBe(false);
  });
  it('Datasets job running', () => {
    expect(isJobRunning(datasetJobStopedState)).toBe(false);
    expect(isJobRunning(datasetJobPendingState)).toBe(true);
    expect(isJobRunning(datasetJobRunningState)).toBe(true);
    expect(isJobRunning(datasetJobSuccessState)).toBe(false);
    expect(isJobRunning(datasetJobFailedState)).toBe(false);
  });
});

describe('Datasets helpers', () => {
  it('getTotalDataSize', () => {
    expect(getTotalDataSize(unfinishedImporting)).toBe(unfinishedImporting.file_size);
    expect(getTotalDataSize(importFailed)).toBe(importFailed.file_size);
    expect(getTotalDataSize(successfullyImport)).toBe(successfullyImport.file_size);
  });

  it('getIntersectionRate', () => {
    expect(
      getIntersectionRate({
        input: 0,
        output: 0,
      }),
    ).toEqual('0%');
    expect(
      getIntersectionRate({
        input: 1000,
        output: 0,
      }),
    ).toEqual('0%');
    expect(
      getIntersectionRate({
        input: 1000,
        output: 100,
      }),
    ).toEqual('10%');
    expect(
      getIntersectionRate({
        input: 1000,
        output: 250,
      }),
    ).toEqual('25%');
    expect(
      getIntersectionRate({
        input: 1000,
        output: 312,
      }),
    ).toEqual('31.2%');
    expect(
      getIntersectionRate({
        input: 10000,
        output: 3124,
      }),
    ).toEqual('31.24%');
  });
});

describe('Datasets import stage getter', () => {
  it('getImportStage', () => {
    expect(getImportStage(frontendSucceeded)).toEqual({
      text: '可用',
      type: 'success',
    });
    expect(getImportStage(frontendFailed)).toEqual({
      text: '处理失败',
      type: 'error',
      tip: '',
    });
    expect(getImportStage(frontendProcessing)).toEqual({
      text: '处理中',
      type: 'processing',
    });
    expect(getImportStage(deleting)).toEqual({
      text: '删除中',
      type: 'processing',
    });
  });
});

describe('Datasets Transactions status getter', () => {
  it('getTransactionStatus', () => {
    expect(getTransactionStatus(transactionFailed)).toEqual({
      type: 'error',
      text: 'dataset.state_transaction_failed',
    });
    expect(getTransactionStatus(transactionProcessing)).toEqual({
      type: 'processing',
      text: 'dataset.state_transaction_processing',
    });
    expect(getTransactionStatus(transactionSucceeded)).toEqual({
      type: 'success',
      text: 'dataset.state_transaction_success',
    });
  });
});
