import {
  formatExtra,
  formatListWithExtra,
  formatMetrics,
  formatIntersectionDatasetName,
  getDefaultVariableValue,
} from './modelCenter';

import {
  readyToRun,
  invalid,
  running,
  completed,
  stopped,
  failed,
} from 'services/mocks/v2/intersection_datasets/examples';
import { completed as workflowCompletedItem } from 'services/mocks/v2/workflows/examples';
import { modelJobMetric, modelJobMetric2 } from 'services/mocks/v2/model_jobs/examples';
import { CONSTANTS } from 'shared/constants';

const testItem1 = {
  name: 'item1',
  extra: JSON.stringify({ e1: 1, e2: 2, e3: 3 }),
};
const testItem2 = {
  name: 'item2',
  extra: JSON.stringify({ name: 'extraName2' }),
};

const testItem3 = {
  ...testItem1,
  name: 'item3',
  local_extra: JSON.stringify({ le1: 1, le2: 2, le3: 3 }),
};
const testItem4 = {
  ...testItem2,
  name: 'item4',
  local_extra: JSON.stringify({ name: 'localExtraName4' }),
};

const testItem5 = {
  name: 'name5',
  extra: JSON.stringify({ name: 'extraName5', e1: 1, e2: 2 }),
  local_extra: JSON.stringify({ name: 'localExtraName5', e1: 3 }),
};
describe('Model center helpers', () => {
  describe('FormatExtra', () => {
    it('Empty input', () => {
      expect(formatExtra({})).toEqual({});
    });

    it('Own extra field, but no local_extra field', () => {
      expect(formatExtra(testItem1)).toEqual({
        ...testItem1,
        e1: 1,
        e2: 2,
        e3: 3,
      });
      expect(formatExtra(testItem2)).toEqual({
        ...testItem2,
        name: 'extraName2',
      });
    });
    it('Own extra field and local_extra field', () => {
      expect(formatExtra(testItem3)).toEqual({
        ...testItem3,
        e1: 1,
        e2: 2,
        e3: 3,
        le1: 1,
        le2: 2,
        le3: 3,
      });
    });
    it('Own extra field and local_extra field, local_extra will override extra', () => {
      expect(formatExtra(testItem4)).toEqual({
        ...testItem4,
        name: 'localExtraName4',
      });
      expect(formatExtra(testItem5)).toEqual({
        ...testItem5,
        name: 'localExtraName5',
        e1: 3,
        e2: 2,
      });
    });
    it('Override extra field', () => {
      expect(formatExtra(testItem4, true)).toEqual({
        ...testItem4,
      });
      expect(formatExtra(testItem5, true)).toEqual({
        e1: 3,
        e2: 2,
        ...testItem5,
      });
    });
  });

  describe('FormatListWithExtra', () => {
    it('Empty input', () => {
      expect(formatListWithExtra([])).toEqual([]);
    });
    it('Own extra field, but no local_extra field', () => {
      expect(formatListWithExtra([testItem1, testItem2])).toEqual([
        {
          ...testItem1,
          e1: 1,
          e2: 2,
          e3: 3,
        },
        {
          ...testItem2,
          name: 'extraName2',
        },
      ]);
    });
    it('Own extra field and local_extra field', () => {
      expect(formatListWithExtra([testItem3])).toEqual([
        {
          ...testItem3,
          e1: 1,
          e2: 2,
          e3: 3,
          le1: 1,
          le2: 2,
          le3: 3,
        },
      ]);
    });
    it('Own extra field and local_extra field, local_extra will override extra', () => {
      expect(formatListWithExtra([testItem4, testItem5])).toEqual([
        {
          ...testItem4,
          name: 'localExtraName4',
        },
        {
          ...testItem5,
          name: 'localExtraName5',
          e1: 3,
          e2: 2,
        },
      ]);
    });

    it('Override extra field', () => {
      expect(formatListWithExtra([testItem4, testItem5], true)).toEqual([
        {
          ...testItem4,
        },
        {
          e1: 3,
          e2: 2,
          ...testItem5,
        },
      ]);
    });
  });

  it('FormatIntersectionDatasetName', () => {
    expect(formatIntersectionDatasetName(running)).toBe(running.name);
    expect(formatIntersectionDatasetName(completed)).toBe(completed.name);
    expect(formatIntersectionDatasetName(stopped)).toBe(stopped.name);
    expect(formatIntersectionDatasetName(invalid)).toBe(invalid.name);
    expect(formatIntersectionDatasetName(failed)).toBe(failed.name);
    expect(formatIntersectionDatasetName(readyToRun)).toBe(readyToRun.name);
    expect(formatIntersectionDatasetName({} as any)).toBe(CONSTANTS.EMPTY_PLACEHOLDER);
  });

  it('FormatMetrics', () => {
    expect(formatMetrics({} as any)).toEqual({
      confusion_matrix: [],
      eval: [],
      evalMaxValue: 0,
      featureImportanceMaxValue: 0,
      feature_importance: [],
      train: [],
      trainMaxValue: 0,
    });

    expect(
      formatMetrics({
        train: {
          acc: null,
        },
        eval: {
          acc: null,
        },
      } as any),
    ).toEqual({
      confusion_matrix: [],
      eval: [{ label: 'acc', value: null }],
      evalMaxValue: 0,
      featureImportanceMaxValue: 0,
      feature_importance: [],
      train: [{ label: 'acc', value: null }],
      trainMaxValue: 0,
    });

    expect(
      formatMetrics({
        train: {
          acc: {
            steps: [1, 2, 3],
            values: [4, 5, 6],
          },
          auc: {
            steps: [1, 2, 3],
            values: [7, 8, 9],
          },
        },
        eval: {
          acc: {
            steps: [1, 2, 3],
            values: [14, 15, 16],
          },
          auc: {
            steps: [1, 2, 3],
            values: [17, 18, 19],
          },
        },
      } as any),
    ).toEqual({
      confusion_matrix: [],
      eval: [
        { label: 'acc', value: 16 },
        { label: 'auc', value: 19 },
      ],
      evalMaxValue: 19,
      featureImportanceMaxValue: 0,
      feature_importance: [],
      train: [
        { label: 'acc', value: 6 },
        { label: 'auc', value: 9 },
      ],
      trainMaxValue: 9,
    });

    expect(
      formatMetrics({
        train: {
          acc: {
            steps: [1],
            values: [4],
          },
          auc: {
            steps: [1],
            values: [7],
          },
        },
        eval: {
          acc: {
            steps: [1],
            values: [14],
          },
          auc: {
            steps: [1],
            values: [17],
          },
        },
      } as any),
    ).toEqual({
      confusion_matrix: [],
      eval: [
        { label: 'acc', value: 14 },
        { label: 'auc', value: 17 },
      ],
      evalMaxValue: 17,
      featureImportanceMaxValue: 0,
      feature_importance: [],
      train: [
        { label: 'acc', value: 4 },
        { label: 'auc', value: 7 },
      ],
      trainMaxValue: 7,
    });

    expect(
      formatMetrics({
        confusion_matrix: {
          fp: null,
          fn: undefined,
          tn: 40,
          tp: 0,
        },
      } as any),
    ).toEqual({
      confusion_matrix: [
        { label: 'tp', value: 0, percentValue: '0%' },
        { label: 'fn', value: 0, percentValue: '0%' },
        { label: 'fp', value: 0, percentValue: '0%' },
        { label: 'tn', value: 40, percentValue: '100%' },
      ],
      eval: [],
      evalMaxValue: 0,
      featureImportanceMaxValue: 0,
      feature_importance: [],
      train: [],
      trainMaxValue: 0,
    });

    expect(
      formatMetrics({
        confusion_matrix: {
          fp: null,
          fn: undefined,
          tn: 0,
          tp: 0,
        },
      } as any),
    ).toEqual({
      confusion_matrix: [
        { label: 'tp', value: 0, percentValue: CONSTANTS.EMPTY_PLACEHOLDER },
        { label: 'fn', value: 0, percentValue: CONSTANTS.EMPTY_PLACEHOLDER },
        { label: 'fp', value: 0, percentValue: CONSTANTS.EMPTY_PLACEHOLDER },
        { label: 'tn', value: 0, percentValue: CONSTANTS.EMPTY_PLACEHOLDER },
      ],
      eval: [],
      evalMaxValue: 0,
      featureImportanceMaxValue: 0,
      feature_importance: [],
      train: [],
      trainMaxValue: 0,
    });

    expect(formatMetrics(modelJobMetric)).toEqual({
      confusion_matrix: [
        { label: 'tp', value: 30, percentValue: '30%' },
        { label: 'fn', value: 22, percentValue: '22%' },
        { label: 'fp', value: 8, percentValue: '8%' },
        { label: 'tn', value: 40, percentValue: '40%' },
      ],
      eval: [
        { label: 'acc', value: 0.9 },
        { label: 'auc', value: 0.8 },
        { label: 'precision', value: 0.7 },
        { label: 'recall', value: 0.2 },
        { label: 'f1', value: 0.1 },
        { label: 'ks', value: 0.7 },
      ],
      evalMaxValue: 0.9,
      featureImportanceMaxValue: 0.7,
      feature_importance: [
        { label: 'test_13', value: 0.7 },
        { label: 'test_14', value: 0.6 },
        { label: 'test_15', value: 0.5 },
        { label: 'test_16', value: 0.4 },
        { label: 'peer-1', value: 0.3 },
        { label: 'peer-2', value: 0.3 },
        { label: 'age', value: 0.3 },
        { label: 'overall_score', value: 0.3 },
        { label: 'test_17', value: 0.3 },
        { label: 'salary', value: 0.2 },
        { label: 'test_19', value: 0.2 },
        { label: 'peer-3', value: 0.1 },
        { label: 'education', value: 0.1 },
        { label: 'height', value: 0.1 },
        { label: 'peer-0', value: 0.08 },
      ],
      train: [
        { label: 'acc', value: 0.9 },
        { label: 'auc', value: 0.8 },
        { label: 'precision', value: 0.7 },
        { label: 'recall', value: 0.2 },
        { label: 'f1', value: 0.1 },
        { label: 'ks', value: 0.7 },
      ],
      trainMaxValue: 0.9,
    });

    expect(formatMetrics(modelJobMetric2)).toEqual({
      confusion_matrix: [
        { label: 'tp', value: 22, percentValue: '21.56%' },
        { label: 'fn', value: 22, percentValue: '21.56%' },
        { label: 'fp', value: 8, percentValue: '7.84%' },
        { label: 'tn', value: 50, percentValue: '49.01%' },
      ],
      eval: [
        { label: 'acc', value: 0.1 },
        { label: 'auc', value: 0.2 },
        { label: 'precision', value: 0.3 },
        { label: 'recall', value: 0.4 },
        { label: 'f1', value: 0.5 },
        { label: 'ks', value: 0.4 },
      ],
      evalMaxValue: 0.5,
      featureImportanceMaxValue: 0.7,
      feature_importance: [
        { label: 'test_13', value: 0.7 },
        { label: 'test_14', value: 0.6 },
        { label: 'test_15', value: 0.5 },
        { label: 'test_16', value: 0.4 },
        { label: 'peer-1', value: 0.3 },
        { label: 'peer-2', value: 0.3 },
        { label: 'age', value: 0.3 },
        { label: 'overall_score', value: 0.3 },
        { label: 'test_17', value: 0.3 },
        { label: 'salary', value: 0.2 },
        { label: 'test_19', value: 0.2 },
        { label: 'peer-3', value: 0.1 },
        { label: 'education', value: 0.1 },
        { label: 'height', value: 0.1 },
        { label: 'peer-0', value: 0.08 },
      ],
      train: [
        { label: 'acc', value: 0.1 },
        { label: 'auc', value: 0.2 },
        { label: 'precision', value: 0.3 },
        { label: 'recall', value: 0.4 },
        { label: 'f1', value: 0.5 },
        { label: 'ks', value: 0.4 },
      ],
      trainMaxValue: 0.5,
    });
  });

  it('getDefaultVariableValue', () => {
    expect(getDefaultVariableValue(workflowCompletedItem)).toBe(undefined);
    expect(getDefaultVariableValue(workflowCompletedItem, 'image_version')).toBe('v1.5-rc3');
    expect(getDefaultVariableValue({} as any)).toBe(undefined);
    expect(
      getDefaultVariableValue({
        config: {
          variables: [],
          job_definitions: [],
        },
      } as any),
    ).toBe(undefined);
    expect(
      getDefaultVariableValue({
        config: {
          variables: [],
          job_definitions: [
            {
              variables: [{ name: 'image', value: '123' }],
            },
          ],
        },
      } as any),
    ).toBe('123');
    expect(
      getDefaultVariableValue({
        config: {
          variables: [{ name: 'image', value: '456' }],
          job_definitions: [
            {
              variables: [{ name: 'image', value: '123' }],
            },
          ],
        },
      } as any),
    ).toBe('456');
    expect(
      getDefaultVariableValue({
        config: {
          variables: [],
          job_definitions: [
            {
              variables: [
                { name: 'image', value: '123' },
                { name: 'image', value: '456' },
              ],
            },
          ],
        },
      } as any),
    ).toBe('123');
    expect(
      getDefaultVariableValue(
        {
          config: {
            variables: [{ name: 'image', value: '456' }],
            job_definitions: [
              {
                variables: [
                  { name: 'image', value: '123' },
                  { name: 'image_version', value: '789' },
                ],
              },
            ],
          },
        } as any,
        'image_version',
      ),
    ).toBe('789');

    expect(
      getDefaultVariableValue({
        config: {
          variables: [{ name: 'image', value: undefined }],
          job_definitions: [
            {
              variables: [{ name: 'image', value: '123' }],
            },
          ],
        },
      } as any),
    ).toBe(undefined);
    expect(
      getDefaultVariableValue({
        config: {
          variables: [],
          job_definitions: [
            {
              variables: [
                { name: 'image', value: undefined },
                { name: 'image', value: '456' },
              ],
            },
          ],
        },
      } as any),
    ).toBe(undefined);
  });
});
