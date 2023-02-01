import { ModelJobMetrics } from 'typings/modelCenter';

export const modelJobMetric: ModelJobMetrics = {
  train: {
    acc: [
      [1, 2],
      [0.6, 0.9],
    ],
    auc: [
      [1, 2],
      [0.6, 0.8],
    ],
    precision: [
      [1, 2],
      [0.6, 0.7],
    ],
    recall: [
      [1, 2],
      [0.7, 0.2],
    ],
    f1: [
      [1, 2],
      [0.6, 0.1],
    ],
    ks: [
      [1, 2],
      [0.6, 0.7],
    ],
  },
  eval: {
    acc: [
      [1, 2],
      [0.6, 0.9],
    ],
    auc: [
      [1, 2],
      [0.6, 0.8],
    ],
    precision: [
      [1, 2],
      [0.6, 0.7],
    ],
    recall: [
      [1, 2],
      [0.7, 0.2],
    ],
    f1: [
      [1, 2],
      [0.6, 0.1],
    ],
    ks: [
      [1, 2],
      [0.6, 0.7],
    ],
  },
  feature_importance: {
    'peer-0': 0.08,
    'peer-1': 0.3,
    'peer-2': 0.3,
    'peer-3': 0.1,
    'peer-4': 0.03,
    age: 0.3,
    overall_score: 0.3,
    education: 0.1,
    salary: 0.2,
    height: 0.1,
    weight: 0.02,
    cars: 0.001,

    test_13: 0.7,
    test_14: 0.6,
    test_15: 0.5,
    test_16: 0.4,
    test_17: 0.3,
    test_19: 0.2,
  },
  confusion_matrix: {
    tp: 30,
    fp: 8,
    fn: 22,
    tn: 40,
  },
};

export const modelJobMetric2: ModelJobMetrics = {
  train: {
    acc: [
      [1, 2],
      [0.6, 0.1],
    ],
    auc: [
      [1, 2],
      [0.6, 0.2],
    ],
    precision: [
      [1, 2],
      [0.6, 0.3],
    ],
    recall: [
      [1, 2],
      [0.7, 0.4],
    ],
    f1: [
      [1, 2],
      [0.6, 0.5],
    ],
    ks: [
      [1, 2],
      [0.6, 0.4],
    ],
  },
  eval: {
    acc: [
      [1, 2],
      [0.6, 0.1],
    ],
    auc: [
      [1, 2],
      [0.6, 0.2],
    ],
    precision: [
      [1, 2],
      [0.6, 0.3],
    ],
    recall: [
      [1, 2],
      [0.7, 0.4],
    ],
    f1: [
      [1, 2],
      [0.6, 0.5],
    ],
    ks: [
      [1, 2],
      [0.6, 0.4],
    ],
  },
  feature_importance: {
    'peer-0': 0.08,
    'peer-1': 0.3,
    'peer-2': 0.3,
    'peer-3': 0.1,
    'peer-4': 0.03,
    age: 0.3,
    overall_score: 0.3,
    education: 0.1,
    salary: 0.2,
    height: 0.1,
    weight: 0.02,
    cars: 0.001,

    test_13: 0.7,
    test_14: 0.6,
    test_15: 0.5,
    test_16: 0.4,
    test_17: 0.3,
    test_19: 0.2,
  },
  confusion_matrix: {
    tp: 22,
    fp: 8,
    fn: 22,
    tn: 50,
  },
};
