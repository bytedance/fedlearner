import { ResponseInfo } from 'typings/app';
import { ModelServing, ModelServingState } from 'typings/modelServing';

const statusList = [
  ModelServingState.AVAILABLE,
  ModelServingState.LOADING,
  ModelServingState.UNLOADING,
  ModelServingState.UNKNOWN,
];

const list: ModelServing[] = new Array(12).fill(undefined).map((_, index) => {
  return {
    id: index + 1,
    project_id: 1,
    name: 'mock模型serving' + index,
    comment: '备注',
    instances: [],
    deployment_id: 1,
    resource: {
      cpu: '2000m',
      memory: '10Gi',
      replicas: 2,
    },
    is_local: index % 2 === 0,
    support_inference: index % 2 === 0,
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
    status: statusList[index % 4],
    endpoint: '',
    extra: '',
    instance_num_status: '1/3',
    created_at: 1608582145,
    updated_at: 1608582145,
    deleted_at: 1608582145,
  };
});

const get = {
  data: {
    data: list,
    page_meta: {
      current_page: 1,
      page_size: 10,
      total_pages: 2,
      total_items: 12,
    },
  },
  status: 200,
} as ResponseInfo;

export default get;
