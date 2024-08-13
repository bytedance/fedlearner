import {
  getAdvanceConfigList,
  hydrateWorkflowConfig,
  getDataSource,
  isTreeAlgorithm,
  isNNAlgorithm,
  isOldAlgorithm,
  isHorizontalAlgorithm,
  isVerticalAlgorithm,
} from './shared';

import { JobType } from 'typings/job';
import { VariableAccessMode, VariableValueType } from 'typings/variable';
import { WorkflowConfig } from 'typings/workflow';
import { EnumAlgorithmProjectType } from 'typings/algorithm';
import { AlgorithmType } from 'typings/modelCenter';

const TREE_TEMPLATE_CONFIG: WorkflowConfig = {
  group_alias: 'sys_preset_tree_model',
  job_definitions: [
    {
      name: 'tree-model',
      job_type: JobType.TREE_MODEL_TRAINING,
      is_federated: true,
      variables: [
        {
          name: 'image',
          value: 'artifact.bytedance.com/fedlearner/fedlearner:d5d0bb5',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true,"tooltip":"建议不修改，指定Pod中运行的容器镜像地址，修改此项可能导致本基本模版不适用"}' as any,
          typed_value: 'artifact.bytedance.com/fedlearner/fedlearner:d5d0bb5',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'mode',
          value: 'train',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Select","required":true,"enum":["train","eval"]}' as any,
          typed_value: 'train',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'data_source',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false,"tooltip":"求交数据集名称"}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'data_path',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false,"tooltip":"数据存放位置"}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'validation_data_path',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'file_ext',
          value: '.data',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true,"tooltip":"example: .data, .csv or .tfrecord 文件后缀"}' as any,
          typed_value: '.data',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'file_type',
          value: 'tfrecord',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Select","required":true,"enum":["csv","tfrecord"],"tooltip":"文件类型，csv或tfrecord"}' as any,
          typed_value: 'tfrecord',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'load_model_path',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false,"tooltip":"模型文件地址"}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'loss_type',
          value: 'logistic',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Select","required":false,"enum":["logistic","mse"],"tooltip":"损失函数类型，logistic或mse，默认logistic"}' as any,
          typed_value: 'logistic',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'learning_rate',
          value: '0.3',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false}' as any,
          typed_value: '0.3',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'max_iters',
          value: '10',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false,"tooltip":"树的数量"}' as any,
          typed_value: '10',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'max_depth',
          value: '5',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false}' as any,
          typed_value: '5',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'max_bins',
          value: '33',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false,"tooltip":"最大分箱数"}' as any,
          typed_value: '33',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'l2_regularization',
          value: '1',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false,"tooltip":"L2惩罚系数"}' as any,
          typed_value: '1',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'num_parallel',
          value: '5',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false,"tooltip":"进程数量"}' as any,
          typed_value: '5',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'enable_packing',
          value: 'true',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Select","required":false,"enum":["true","false"],"tooltip":"是否开启优化"}' as any,
          typed_value: 'true',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'ignore_fields',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false,"tooltip":"不入模特征，以逗号分隔如：name,age,sex"}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'cat_fields',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false,"tooltip":"类别类型特征，特征的值需要是非负整数。以逗号分隔如：alive,country,sex"}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'send_scores_to_follower',
          value: 'false',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Select","required":false,"enum":["false","true"]}' as any,
          typed_value: 'false',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'send_metrics_to_follower',
          value: 'false',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Select","required":false,"enum":["false","true"]}' as any,
          typed_value: 'false',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'verify_example_ids',
          value: 'false',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema:
            '{"component":"Select","required":false,"tooltip":"是否检查example_id对齐 If set to true, the first column of the data will be treated as example ids that must match between leader and follower","enum":["false","true"]}',
          typed_value: 'false',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'verbosity',
          value: '1',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema:
            '{"component":"Select","required":false,"enum":["0","1","2"],"tooltip":"日志输出等级"}',
          typed_value: '1',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'no_data',
          value: 'false',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema:
            '{"component":"Select","required":false,"tooltip":"Leader是否没数据，不建议乱用","enum":["false","true"]}',
          typed_value: 'false',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'worker_cpu',
          value: '8000m',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true}' as any,
          typed_value: '8000m',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'worker_mem',
          value: '16Gi',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true}' as any,
          typed_value: '16Gi',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'role',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Select","required":true,"enum":["Leader","Follower"]}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'label_field',
          value: 'label',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false,"tooltip":"label特征名"}' as any,
          typed_value: 'label',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'load_model_name',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false,"tooltip":"按任务名称加载模型，{STORAGE_ROOT_PATH}/job_output/{LOAD_MODEL_NAME}/exported_models"}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
      ],
      yaml_template: '',
      easy_mode: true,
      dependencies: [],
    },
  ],
  variables: [],
};

const NN_TEMPLATE_CONFIG: WorkflowConfig = {
  group_alias: 'sys_preset_nn_model',
  variables: [
    {
      name: 'image',
      value: 'artifact.bytedance.com/fedlearner/fedlearner:21d2ae4',
      access_mode: VariableAccessMode.PEER_WRITABLE,
      widget_schema: '{"component":"Input","required":true}' as any,
      typed_value: 'artifact.bytedance.com/fedlearner/fedlearner:21d2ae4',
      value_type: VariableValueType.STRING,
    },
  ],
  job_definitions: [
    {
      name: 'nn-model',
      job_type: JobType.NN_MODEL_TRANINING,
      is_federated: true,
      variables: [
        {
          name: 'master_cpu',
          value: '3000m',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true}' as any,
          typed_value: '3000m',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'master_mem',
          value: '4Gi',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true}' as any,
          typed_value: '4Gi',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'worker_cpu',
          value: '2000m',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true}' as any,
          typed_value: '2000m',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'worker_mem',
          value: '4Gi',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true}' as any,
          typed_value: '4Gi',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'ps_replicas',
          value: '1',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true}' as any,
          typed_value: '1',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'master_replicas',
          value: '1',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true}' as any,
          typed_value: '1',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'ps_cpu',
          value: '2000m',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true}' as any,
          typed_value: '2000m',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'ps_mem',
          value: '4Gi',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true}' as any,
          typed_value: '4Gi',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'worker_replicas',
          value: '1',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":true}' as any,
          typed_value: '1',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'data_source',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'epoch_num',
          value: '1',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false}' as any,
          typed_value: '1',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'shuffle_data_block',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'verbosity',
          value: '1',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Select","required":false,"enum":["0","1","2"]}' as any,
          typed_value: '1',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'mode',
          value: 'train',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Select","required":true,"enum":["train","eval"]}' as any,
          typed_value: 'train',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'save_checkpoint_secs',
          value: '600',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false}' as any,
          typed_value: '600',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'save_checkpoint_steps',
          value: '1000',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false}' as any,
          typed_value: '1000',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'load_checkpoint_filename',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'load_checkpoint_filename_with_path',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'sparse_estimator',
          value: 'True',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false}' as any,
          typed_value: 'True',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'role',
          value: 'Leader',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Select","required":true,"enum":["Leader","Follower"]}' as any,
          typed_value: 'Leader',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'load_model_name',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"Input","required":false}' as any,
          typed_value: '',
          value: '',
          value_type: VariableValueType.STRING,
        },
        {
          name: 'algorithm',
          value: '{"config":[],"path":""}',
          access_mode: VariableAccessMode.PEER_WRITABLE,
          widget_schema: '{"component":"AlgorithmSelect","required":true}' as any,
          value_type: VariableValueType.OBJECT,
          typed_value: {
            config: [],
            path: '',
          },
        },
      ],
      yaml_template: '',
      easy_mode: true,
      dependencies: [],
    },
  ],
};

it('getAdvanceConfigList', () => {
  expect(getAdvanceConfigList(TREE_TEMPLATE_CONFIG)).toEqual([
    {
      label: '镜像',
      field: 'image',
      initialValue: 'artifact.bytedance.com/fedlearner/fedlearner:d5d0bb5',
      tip: expect.any(String),
    },
    {
      field: 'data_source',
      initialValue: '',
      label: '数据源',
      tip: expect.any(String),
    },
    {
      label: '数据源',
      field: 'data_path',
      initialValue: '',
      tip: expect.any(String),
    },
    {
      label: '验证数据集地址',
      field: 'validation_data_path',
      initialValue: '',
      tip: undefined,
    },
    {
      label: '文件扩展名',
      field: 'file_ext',
      initialValue: '.data',
      tip: expect.any(String),
    },
    {
      label: '文件类型',
      field: 'file_type',
      initialValue: 'tfrecord',
      tip: expect.any(String),
    },
    {
      label: '加载模型路径',
      field: 'load_model_path',
      initialValue: '',
      tip: expect.any(String),
    },
    {
      label: '是否优化',
      field: 'enable_packing',
      initialValue: 'true',
      tip: expect.any(String),
    },
    {
      label: '忽略字段',
      field: 'ignore_fields',
      initialValue: '',
      tip: expect.any(String),
    },
    {
      label: '类型变量字段',
      field: 'cat_fields',
      initialValue: '',
      tip: expect.any(String),
    },
    {
      label: '是否将预测值发送至 follower',
      field: 'send_scores_to_follower',
      initialValue: 'false',
      tip: expect.any(String),
    },
    {
      label: '是否将指标发送至 follower',
      field: 'send_metrics_to_follower',
      initialValue: 'false',
      tip: expect.any(String),
    },
    {
      label: '是否检验 example_ids',
      field: 'verify_example_ids',
      initialValue: 'false',
      tip: expect.any(String),
    },
    {
      label: '日志输出等级',
      field: 'verbosity',
      initialValue: '1',
      tip: expect.any(String),
    },
    {
      label: '标签方是否无特征',
      field: 'no_data',
      initialValue: 'false',
      tip: expect.any(String),
    },
    {
      label: '标签字段',
      field: 'label_field',
      initialValue: 'label',
      tip: expect.any(String),
    },
    {
      label: '加载模型名称',
      field: 'load_model_name',
      initialValue: '',
      tip: expect.any(String),
    },
  ]);
  expect(getAdvanceConfigList(NN_TEMPLATE_CONFIG, true)).toEqual([
    {
      label: '镜像',
      field: 'image',
      initialValue: 'artifact.bytedance.com/fedlearner/fedlearner:21d2ae4',
      tip: undefined,
    },
    {
      field: 'data_source',
      initialValue: '',
      label: '数据源',
      tip: undefined,
    },
    {
      label: '是否打乱顺序',
      field: 'shuffle_data_block',
      initialValue: '',
      tip: expect.any(String),
    },
    {
      label: '保存备份间隔秒数',
      field: 'save_checkpoint_secs',
      initialValue: '600',
      tip: expect.any(String),
    },
    {
      label: '保存备份间隔步数',
      field: 'save_checkpoint_steps',
      initialValue: '1000',
      tip: expect.any(String),
    },
    {
      label: '加载文件名',
      field: 'load_checkpoint_filename',
      initialValue: '',
      tip: expect.any(String),
    },
    {
      label: '加载文件路径',
      field: 'load_checkpoint_filename_with_path',
      initialValue: '',
      tip: expect.any(String),
    },
    {
      field: 'sparse_estimator',
      initialValue: 'True',
      tip: expect.any(String),
      label: 'sparse_estimator',
    },
    {
      label: '加载模型名称',
      field: 'load_model_name',
      initialValue: '',
      tip: expect.any(String),
    },
  ]);
});

it('hydrateWorkflowConfig', () => {
  expect(hydrateWorkflowConfig(TREE_TEMPLATE_CONFIG, {})).toEqual(TREE_TEMPLATE_CONFIG);
  expect(
    hydrateWorkflowConfig(TREE_TEMPLATE_CONFIG, {
      image: '1',
      mode: '2',
      data_source: '3',
    }),
  ).toEqual({
    ...TREE_TEMPLATE_CONFIG,
    job_definitions: [
      {
        ...TREE_TEMPLATE_CONFIG.job_definitions[0],
        variables: [
          {
            name: 'image',
            value: '1',
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: '{"component":"Input","required":true,"tooltip":"建议不修改，指定Pod中运行的容器镜像地址，修改此项可能导致本基本模版不适用"}' as any,
            typed_value: 'artifact.bytedance.com/fedlearner/fedlearner:d5d0bb5',
            value_type: VariableValueType.STRING,
          },
          {
            name: 'mode',
            value: '2',
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: '{"component":"Select","required":true,"enum":["train","eval"]}' as any,
            typed_value: 'train',
            value_type: VariableValueType.STRING,
          },
          {
            name: 'data_source',
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: '{"component":"Input","required":false,"tooltip":"求交数据集名称"}' as any,
            typed_value: '',
            value: '3',
            value_type: VariableValueType.STRING,
          },
        ].concat(TREE_TEMPLATE_CONFIG.job_definitions[0].variables.slice(3) as any),
      },
    ],
  });
});

it('getDataSource', () => {
  expect(getDataSource('')).toBe('');
  expect(getDataSource('adasdsadsadsadsad')).toBe('');
  expect(getDataSource('data_source')).toBe('');
  expect(getDataSource('data_source/')).toBe('');
  expect(getDataSource('data_source/abc')).toBe('');
  expect(getDataSource('/data_source')).toBe('');
  expect(getDataSource('/data_source/')).toBe('');
  expect(getDataSource('/data_source/abc')).toBe('abc');
  expect(
    getDataSource(
      'hdfs:///trimmed',
    ),
  ).toBe('u0bae4aa7dcde477e8ee-psi-data-join-job');
});

it('isTreeAlgorithm', () => {
  expect(isTreeAlgorithm(AlgorithmType.TREE)).toBe(true);
  expect(isTreeAlgorithm(AlgorithmType.NN)).toBe(false);
  expect(isTreeAlgorithm(EnumAlgorithmProjectType.TREE_VERTICAL)).toBe(true);
  expect(isTreeAlgorithm(EnumAlgorithmProjectType.TREE_HORIZONTAL)).toBe(true);
  expect(isTreeAlgorithm(EnumAlgorithmProjectType.NN_VERTICAL)).toBe(false);
  expect(isTreeAlgorithm(EnumAlgorithmProjectType.NN_HORIZONTAL)).toBe(false);
  expect(isTreeAlgorithm(EnumAlgorithmProjectType.NN_LOCAL)).toBe(false);
  expect(isTreeAlgorithm(EnumAlgorithmProjectType.UNSPECIFIED)).toBe(false);
});
it('isNNAlgorithm', () => {
  expect(isNNAlgorithm(AlgorithmType.TREE)).toBe(false);
  expect(isNNAlgorithm(AlgorithmType.NN)).toBe(true);
  expect(isNNAlgorithm(EnumAlgorithmProjectType.TREE_VERTICAL)).toBe(false);
  expect(isNNAlgorithm(EnumAlgorithmProjectType.TREE_HORIZONTAL)).toBe(false);
  expect(isNNAlgorithm(EnumAlgorithmProjectType.NN_VERTICAL)).toBe(true);
  expect(isNNAlgorithm(EnumAlgorithmProjectType.NN_HORIZONTAL)).toBe(true);
  expect(isNNAlgorithm(EnumAlgorithmProjectType.NN_LOCAL)).toBe(true);
  expect(isNNAlgorithm(EnumAlgorithmProjectType.UNSPECIFIED)).toBe(false);
});
it('isOldAlgorithm', () => {
  expect(isOldAlgorithm(AlgorithmType.TREE)).toBe(true);
  expect(isOldAlgorithm(AlgorithmType.NN)).toBe(true);
  expect(isOldAlgorithm(EnumAlgorithmProjectType.TREE_VERTICAL)).toBe(false);
  expect(isOldAlgorithm(EnumAlgorithmProjectType.TREE_HORIZONTAL)).toBe(false);
  expect(isOldAlgorithm(EnumAlgorithmProjectType.NN_VERTICAL)).toBe(false);
  expect(isOldAlgorithm(EnumAlgorithmProjectType.NN_HORIZONTAL)).toBe(false);
  expect(isOldAlgorithm(EnumAlgorithmProjectType.NN_LOCAL)).toBe(false);
  expect(isOldAlgorithm(EnumAlgorithmProjectType.UNSPECIFIED)).toBe(false);
});
it('isVerticalAlgorithm', () => {
  expect(isVerticalAlgorithm(EnumAlgorithmProjectType.TREE_VERTICAL)).toBe(true);
  expect(isVerticalAlgorithm(EnumAlgorithmProjectType.TREE_HORIZONTAL)).toBe(false);
  expect(isVerticalAlgorithm(EnumAlgorithmProjectType.NN_VERTICAL)).toBe(true);
  expect(isVerticalAlgorithm(EnumAlgorithmProjectType.NN_HORIZONTAL)).toBe(false);
  expect(isVerticalAlgorithm(EnumAlgorithmProjectType.NN_LOCAL)).toBe(false);
  expect(isVerticalAlgorithm(EnumAlgorithmProjectType.UNSPECIFIED)).toBe(false);
});
it('isHorizontalAlgorithm', () => {
  expect(isHorizontalAlgorithm(EnumAlgorithmProjectType.TREE_VERTICAL)).toBe(false);
  expect(isHorizontalAlgorithm(EnumAlgorithmProjectType.TREE_HORIZONTAL)).toBe(true);
  expect(isHorizontalAlgorithm(EnumAlgorithmProjectType.NN_VERTICAL)).toBe(false);
  expect(isHorizontalAlgorithm(EnumAlgorithmProjectType.NN_HORIZONTAL)).toBe(true);
  expect(isHorizontalAlgorithm(EnumAlgorithmProjectType.NN_LOCAL)).toBe(false);
  expect(isHorizontalAlgorithm(EnumAlgorithmProjectType.UNSPECIFIED)).toBe(false);
});
