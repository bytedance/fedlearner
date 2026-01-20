import { AxiosRequestConfig } from 'axios';

import { ModelServing, ModelServingState, ModelServingInstanceState } from 'typings/modelServing';

const get = (config: AxiosRequestConfig) => ({
  data: {
    data: {
      id: Number(config._id! || 0) + 1,
      project_id: 1,
      name: 'mock模型serving' + Number(config._id! || 0) + 1,
      comment: '备注',
      instances: [
        {
          name: 's-20210909112859-64nj6-79cff4cb57-696kr',
          status: ModelServingInstanceState.AVAILABLE,
          cpu: '90%',
          memory: '60%',
          created_at: 1608582145,
          updated_at: 1608582145,
          deleted_at: 1608582145,
        },
        {
          name: 's-20210909112859-64nj6-79cff4cb57-999sr',
          status: ModelServingInstanceState.UNAVAILABLE,
          cpu: '20%',
          memory: '30%',
          created_at: 1608582145,
          updated_at: 1608582145,
          deleted_at: 1608582145,
        },
      ],
      deployment_id: 1,
      resource: {
        cpu: '2000m',
        memory: '10Gi',
        replicas: 2,
      },
      model_id: 1,
      model_type: 'TREE_MODEL',
      signature: JSON.stringify({
        inputs: {
          examples: {
            dtype: 'DT_STRING',
            tensor_shape: { dim: [], unknown_rank: true },
            name: 'examples:0',
          },
        },
        outputs: {
          output: {
            dtype: 'DT_FLOAT',
            tensor_shape: { dim: [{ size: '2', name: '' }], unknown_rank: false },
            name: 'Softmax:0',
          },
        },
        method_name: 'tensorflow/serving/predict',
      }),
      status: ModelServingState.AVAILABLE,
      endpoint: 'https://api/v2/models/inference',
      extra: '',
      instance_num_status: '1/3',
      created_at: 1608582145,
      updated_at: 1608582145,
      deleted_at: 1608582145,
    } as ModelServing,
  },

  status: 200,
});

export const patch = { data: {}, status: 200 };
export const DELETE = { data: {}, status: 200 };

export default get;
