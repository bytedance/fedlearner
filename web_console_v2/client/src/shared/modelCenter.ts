import { floor, isPlainObject } from 'lodash-es';
import { formatObjectToArray } from 'shared/helpers';
import { ModelJobMetrics } from 'typings/modelCenter';
import { IntersectionDataset } from 'typings/dataset';
import { WorkflowExecutionDetails } from 'typings/workflow';
import { CONSTANTS } from 'shared/constants';

export type WithExtra = {
  extra?: any;
  local_extra?: any;
};

type Item = {
  label: string;
  value: number | null;
};

export function formatExtra<T extends WithExtra>(
  originModelSet: T,
  isOverrideExtraField = false,
): T {
  let tempExtra = {} as T;
  let tempLocalExtra = {} as T;
  try {
    tempExtra = JSON.parse(originModelSet.extra);
  } catch (error) {}

  try {
    tempLocalExtra = JSON.parse(originModelSet.local_extra);
  } catch (error) {}

  if (isOverrideExtraField) return { ...tempExtra, ...tempLocalExtra, ...originModelSet };

  return { ...originModelSet, ...tempExtra, ...tempLocalExtra };
}

export function formatListWithExtra<T extends WithExtra>(
  originModelSetList: T[],
  isOverrideExtraField = false,
): T[] {
  return originModelSetList.map((item) => formatExtra(item, isOverrideExtraField));
}

export function formatMetrics<T extends ModelJobMetrics>(metrics: T, maxFeatureCount = 15) {
  let trainMaxValue = 0;
  let evalMaxValue = 0;

  // train
  const trainList = Object.keys(metrics.train ?? {}).reduce((sum, key) => {
    const value = metrics.train[key];

    let finalValue = null;
    if (Array.isArray(value)) {
      finalValue =
        (value && value.length > 1 ? floor(value[1][value[1].length - 1], 3) : null) ?? null; // get last value from array
    }
    if (isPlainObject(value)) {
      const values = value.values as number[];

      finalValue =
        (values && values.length > 0 ? floor(values[values.length - 1], 3) : null) ?? null; // get last value from array
    }

    trainMaxValue = Math.max(Number(finalValue), trainMaxValue);

    sum.push({
      label: key,
      value: finalValue,
    });

    return sum;
  }, [] as Item[]);

  // eval
  const evalList = Object.keys(metrics.eval ?? {}).reduce((sum, key) => {
    const value = metrics.eval[key] || [];

    let finalValue = null;
    if (Array.isArray(value)) {
      finalValue =
        (value && value.length > 1 ? floor(value[1][value[1].length - 1], 3) : null) ?? null; // get last value from array
    }
    if (isPlainObject(value)) {
      const values = value.values as number[];

      finalValue =
        (values && values.length > 0 ? floor(values[values.length - 1], 3) : null) ?? null; // get last value from array
    }

    evalMaxValue = Math.max(Number(finalValue), evalMaxValue);

    sum.push({
      label: key,
      value: finalValue,
    });

    return sum;
  }, [] as Item[]);

  // confusion_matrix
  let confusion_matrix = formatObjectToArray(metrics.confusion_matrix ?? {}, [
    'tp',
    'fn',
    'fp',
    'tn',
  ]) as Array<{
    label: string;
    value: number | null;
    percentValue: string;
  }>;

  const total =
    Number(metrics?.confusion_matrix?.tp ?? 0) +
    Number(metrics?.confusion_matrix?.fn ?? 0) +
    Number(metrics?.confusion_matrix?.fp ?? 0) +
    Number(metrics?.confusion_matrix?.tn ?? 0);

  // calc each confusion_matrix item percent
  confusion_matrix = confusion_matrix.map((item) => {
    return {
      ...item,
      value: item.value || 0,
      percentValue:
        total <= 0
          ? CONSTANTS.EMPTY_PLACEHOLDER
          : `${floor(((item.value || 0) / total) * 100, 2)}%`,
    };
  });

  // feature_importance
  let feature_importance = formatObjectToArray(metrics.feature_importance ?? {});

  // order by value
  feature_importance.sort((a, b) => Number(b.value) - Number(a.value));

  // slice feature_importance, default Top 15
  feature_importance = feature_importance.slice(0, maxFeatureCount);

  return {
    train: trainList,
    eval: evalList,
    confusion_matrix,
    feature_importance,
    trainMaxValue,
    evalMaxValue,
    featureImportanceMaxValue: feature_importance?.[0]?.value ?? 0,
  };
}

export function formatIntersectionDatasetName(dataset: IntersectionDataset) {
  return dataset.name || CONSTANTS.EMPTY_PLACEHOLDER;
}

export function getDefaultVariableValue(
  workflow: WorkflowExecutionDetails,
  imageField = 'image',
): any {
  // variables
  if (workflow.config && workflow.config.variables) {
    const imageVariable = workflow.config.variables.find((item) => item.name === imageField);
    if (imageVariable) {
      return imageVariable.value;
    }
  }
  // job_definitions
  if (workflow.config && workflow.config.job_definitions && workflow.config.job_definitions) {
    for (let i = 0; i < workflow.config.job_definitions.length; i++) {
      for (let j = 0; j < workflow.config.job_definitions[i].variables.length; j++) {
        if (workflow.config.job_definitions[i].variables[j].name === imageField) {
          return workflow.config.job_definitions[i].variables[j].value;
        }
      }
    }
  }

  return undefined;
}
