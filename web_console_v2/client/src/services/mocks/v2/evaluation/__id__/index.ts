import { AxiosRequestConfig } from 'axios';

const get = (config: AxiosRequestConfig) => ({
  data: {
    data: {
      id: 12342323,
      name: 'mock评估任务',
      state: Math.floor(Math.random() * 3),
      dataset: 'test-dataset',
      comment: '我是说明文案我是说明文案我是说明文案我是说明文案',
      modelList: ['Xgbootst-v8', 'Xgbootst-v7', 'Xgbootst-v71'],
      // modelList: ['Xgbootst-v8'],
      extra: JSON.stringify({
        comment:
          '我是说明文案我是说明文案我是说明文案我是说明文案我是说明文案我是说明文案我是说明文案我是说明文案',
        creator: '测试员',
      }),
      algorithm: '树模型',
      metrics: [
        {
          auc_roc: 0.95,
          accuracy: 0.52,
          precision: 0.28,
          recall: 0.48,
          f1_score: 0.95,
          log_loss: 0.35,
        },
        {
          auc_roc: 0.55,
          accuracy: 0.35,
          precision: 0.75,
          recall: 0.65,
          f1_score: 0.45,
          log_loss: 0.105,
        },
        {
          auc_roc: 0.15,
          accuracy: 0.25,
          precision: 0.35,
          recall: 0.45,
          f1_score: 0.55,
          log_loss: 0.35,
        },
      ],
      confusionMatrix: [
        [0.95, 0.05, 0.24, 0.76],
        [0.45, 0.25, 0.34, 0.86],
        [0.45, 0.25, 0.34, 0.86],
      ],
      featureImportance: [
        [
          {
            label: 'Duration',
            value: 77,
          },
          {
            label: 'Mooth',
            value: 40,
          },
          {
            label: 'Day',
            value: 37,
          },
          {
            label: 'Contact',
            value: 30,
          },

          {
            label: 'POutcome',
            value: 23,
          },
          {
            label: 'PDay',
            value: 17,
          },
          {
            label: 'Education',
            value: 11,
          },
        ],
        [
          {
            label: 'Duration',
            value: 67,
          },
          {
            label: 'Mooth',
            value: 20,
          },
          {
            label: 'Day',
            value: 47,
          },
          {
            label: 'Contact',
            value: 10,
          },

          {
            label: 'POutcome',
            value: 63,
          },
          {
            label: 'PDay',
            value: 47,
          },
          {
            label: 'Education',
            value: 31,
          },
        ],
      ],
      created_at: 1608582145,
      updated_at: 1608582145,
      deleted_at: 1608582145,
    },
  },
  status: 200,
});

export const patch = { data: {}, status: 200 };

export default get;
