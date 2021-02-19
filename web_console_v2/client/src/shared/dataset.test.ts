import {
  isAvailable,
  isImportFailed,
  isImportSuccess,
  isImporting,
  getTotalDataSize,
  getImportedProportion,
  getImportStage,
} from './dataset';
import {
  successfullyImport,
  importFailed,
  unfinishedImporting,
} from 'services/mocks/v2/datasets/examples';

describe('Datasets state judgement', () => {
  it('Is import successfully', () => {
    expect(isImportSuccess(successfullyImport)).toBe(true);
    expect(isImportSuccess(importFailed)).toBe(false);
    expect(isImportSuccess(unfinishedImporting)).toBe(false);
  });
  it('Is available', () => {
    expect(isAvailable(successfullyImport)).toBe(true);
    expect(isAvailable(importFailed)).toBe(false);
    expect(isAvailable(unfinishedImporting)).toBe(false);
  });

  it('Is failed', () => {
    expect(isImportFailed(successfullyImport)).toBe(false);
    expect(isImportFailed(importFailed)).toBe(true);
    expect(isImportFailed(unfinishedImporting)).toBe(false);
  });

  it('Is importing', () => {
    expect(isImporting(successfullyImport)).toBe(false);
    expect(isImporting(importFailed)).toBe(false);
    expect(isImporting(unfinishedImporting)).toBe(true);
  });
});

describe('Datasets helpers', () => {
  it('getTotalDataSize', () => {
    expect(getTotalDataSize(unfinishedImporting)).toBe(22345);
    expect(getTotalDataSize(importFailed)).toBe(66666);
    expect(getTotalDataSize(successfullyImport)).toBe(12345);
  });

  it('getImportedProportion', () => {
    expect(getImportedProportion(unfinishedImporting)).toEqual({ imported: 7, total: 15 });
    expect(getImportedProportion(successfullyImport)).toEqual({ imported: 5, total: 5 });
  });
});

describe('Datasets import stage getter', () => {
  it('getImportStage', () => {
    expect(getImportStage(successfullyImport)).toEqual({
      text: 'dataset.state_available',
      type: 'success',
    });

    expect(getImportStage(unfinishedImporting)).toEqual({
      text: 'dataset.state_importing',
      type: 'processing',
    });

    expect(getImportStage(importFailed)).toEqual({
      text: 'dataset.state_error',
      type: 'error',
      tip: 'Failed due to disk space is full',
    });
  });
});
