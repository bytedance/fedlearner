import { atom, selector } from 'recoil';
import i18n from 'i18n';
import { formatExtra } from 'shared/modelCenter';

import { fetchWorkflowTemplateList, fetchTemplateById } from 'services/workflow';

import {
  ResourceTemplateType,
  FederationType,
  UploadType,
  LossType,
  Role,
  RoleUppercase,
  ModelSet,
} from 'typings/modelCenter';
import { WorkflowConfig, WorkflowExecutionDetails, WorkflowTemplate } from 'typings/workflow';
import { EnumAlgorithmProjectType } from 'typings/algorithm';

export const TREE_TRAIN_MODEL_TEMPLATE_NAME = 'sys-preset-tree-model';
export const NN_TRAIN_MODEL_TEMPLATE_NAME = 'sys-preset-nn-model';
export const NN_TRAIN_HORIZONTAL_MODEL_TEMPLATE_NAME = 'sys-preset-nn-horizontal-model';
export const NN_EVAL_HORIZONTAL_MODEL_TEMPLATE_NAME = 'sys-preset-nn-horizontal-eval-model';

export const treeTemplateId = atom<number | null>({
  key: 'TreeTemplateId',
  default: null,
});
export const treeTemplateIdQuery = selector<number | null>({
  key: 'TreeTemplateIdQuery',
  get: async ({ get }) => {
    try {
      const prevTemplateId = get(treeTemplateId);
      if (prevTemplateId !== null) {
        return prevTemplateId;
      }
      const { data } = await fetchWorkflowTemplateList();
      const templateItem =
        data?.find((item) => item.name === TREE_TRAIN_MODEL_TEMPLATE_NAME) ?? null;

      if (!templateItem) {
        throw new Error(i18n.t('error.no_tree_train_model_template'));
      }

      return templateItem?.id ?? null;
    } catch (error) {
      throw error;
    }
  },
  set: ({ set }, newValue: any) => {
    set(treeTemplateId, newValue);
  },
});
export const treeTemplateDetailQuery = selector<WorkflowTemplate | null>({
  key: 'TreeTemplateDetailQuery',
  get: async ({ get }) => {
    try {
      const templateId = get(treeTemplateIdQuery);

      if (!templateId) {
        return null;
      }
      const { data } = await fetchTemplateById(templateId);
      return data;
    } catch (error) {
      throw error;
    }
  },
});

export const nnTemplateId = atom<number | null>({
  key: 'NNTemplateId',
  default: null,
});
export const nnTemplateIdQuery = selector<number | null>({
  key: 'NNTemplateIdQuery',
  get: async ({ get }) => {
    try {
      const prevTemplateId = get(nnTemplateId);
      if (prevTemplateId !== null) {
        return prevTemplateId;
      }
      const { data } = await fetchWorkflowTemplateList();

      const templateItem = data?.find((item) => item.name === NN_TRAIN_MODEL_TEMPLATE_NAME) ?? null;
      if (!templateItem) {
        throw new Error(i18n.t('error.no_nn_train_model_template'));
      }
      return templateItem?.id ?? null;
    } catch (error) {
      throw error;
    }
  },
  set: ({ set }, newValue: any) => {
    set(nnTemplateId, newValue);
  },
});
export const nnTemplateDetailQuery = selector<WorkflowTemplate | null>({
  key: 'NNTemplateDetailQuery',
  get: async ({ get }) => {
    try {
      const templateId = get(nnTemplateIdQuery);

      if (!templateId) {
        return null;
      }
      const { data } = await fetchTemplateById(templateId);
      return data;
    } catch (error) {
      throw error;
    }
  },
});

export const nnHorizontalTemplateId = atom<number | null>({
  key: 'NNHorizontalTemplateId',
  default: null,
});
export const nnHorizontalTemplateIdQuery = selector<number | null>({
  key: 'NNHorizontalTemplateIdQuery',
  get: async ({ get }) => {
    try {
      const prevTemplateId = get(nnHorizontalTemplateId);
      if (prevTemplateId !== null) {
        return prevTemplateId;
      }
      const { data } = await fetchWorkflowTemplateList();

      const templateItem =
        data?.find((item) => item.name === NN_TRAIN_HORIZONTAL_MODEL_TEMPLATE_NAME) ?? null;
      if (!templateItem) {
        throw new Error(i18n.t('error.no_nn_horizontal_train_model_template'));
      }
      return templateItem?.id ?? null;
    } catch (error) {
      throw error;
    }
  },
  set: ({ set }, newValue: any) => {
    set(nnHorizontalTemplateId, newValue);
  },
});
export const nnHorizontalTemplateDetailQuery = selector<WorkflowTemplate | null>({
  key: 'NNHorizontalTemplateDetailQuery',
  get: async ({ get }) => {
    try {
      const templateId = get(nnHorizontalTemplateIdQuery);

      if (!templateId) {
        return null;
      }
      const { data } = await fetchTemplateById(templateId);
      return data;
    } catch (error) {
      throw error;
    }
  },
});

export const nnHorizontalEvalTemplateId = atom<number | null>({
  key: 'NNHorizontalEvalTemplateId',
  default: null,
});
export const nnHorizontalEvalTemplateIdQuery = selector<number | null>({
  key: 'NNHorizontalEvalTemplateIdQuery',
  get: async ({ get }) => {
    try {
      const prevTemplateId = get(nnHorizontalEvalTemplateId);
      if (prevTemplateId !== null) {
        return prevTemplateId;
      }
      const { data } = await fetchWorkflowTemplateList();

      const templateItem =
        data?.find((item) => item.name === NN_EVAL_HORIZONTAL_MODEL_TEMPLATE_NAME) ?? null;
      if (!templateItem) {
        throw new Error(i18n.t('error.no_nn_horizontal_eval_model_template'));
      }
      return templateItem?.id ?? null;
    } catch (error) {
      throw error;
    }
  },
  set: ({ set }, newValue: any) => {
    set(nnHorizontalEvalTemplateId, newValue);
  },
});
export const nnHorizontalEvalTemplateDetailQuery = selector<WorkflowTemplate | null>({
  key: 'NNHorizontalEvalTemplateDetailQuery',
  get: async ({ get }) => {
    try {
      const templateId = get(nnHorizontalEvalTemplateIdQuery);

      if (!templateId) {
        return null;
      }
      const { data } = await fetchTemplateById(templateId);
      return data;
    } catch (error) {
      throw error;
    }
  },
});

export const existedPeerModelSet = atom<ModelSet | null>({
  key: 'ExistedPeerModelSet',
  default: null,
});

export const currentWorkflow = atom<WorkflowExecutionDetails | null>({
  key: 'CurrentWorkflow',
  default: null,
});
export const formattedExtraCurrentWorkflow = selector<WorkflowExecutionDetails | null>({
  key: 'FormattedExtraCurrentWorkflow',
  get: ({ get }) => {
    const baseCurrentWorkflow = get(currentWorkflow);
    if (baseCurrentWorkflow) {
      return formatExtra(baseCurrentWorkflow);
    }
    return null;
  },
});

export const peerWorkflow = atom<WorkflowExecutionDetails | null>({
  key: 'PeerWorkflow',
  default: null,
});
export const formattedExtraPeerWorkflow = selector<WorkflowExecutionDetails | null>({
  key: 'FormattedExtraPeerWorkflow',
  get: ({ get }) => {
    const baseCurrentWorkflow = get(peerWorkflow);
    if (baseCurrentWorkflow) {
      return formatExtra(baseCurrentWorkflow);
    }
    return null;
  },
});

export const currentEnvWorkflow = atom<WorkflowExecutionDetails | null>({
  key: 'CurrentEnvWorkflow',
  default: null,
});
export const formattedExtraCurrentEnvWorkflow = selector<WorkflowExecutionDetails | null>({
  key: 'FormattedExtraCurrentEnvWorkflow',
  get: ({ get }) => {
    const baseCurrentEnvWorkflow = get(currentEnvWorkflow);
    if (baseCurrentEnvWorkflow) {
      return formatExtra(baseCurrentEnvWorkflow);
    }
    return null;
  },
});
export const currentEnvWorkflowConfig = selector<WorkflowConfig | null>({
  key: 'CurrentEnvWorkflowConfig',
  get: ({ get }) => {
    const baseCurrentEnvWorkflow = get(currentEnvWorkflow);
    if (baseCurrentEnvWorkflow) {
      return baseCurrentEnvWorkflow.config;
    }
    return null;
  },
});

export const trainModelForm = atom({
  key: 'TrainModelForm',
  default: {
    project_id: undefined,
    model_name: '',
    train_comment: '',
    dataset_id: undefined,
    dataset_name: '',

    modelset_name: undefined,
    modelset_comment: undefined,

    mode: 'train',
    image: '',
    num_partitions: '',
    namespace: 'default',
    send_metrics_to_follower: false,
    send_scores_to_follower: false,
    is_allow_coordinator_parameter_tuning: false,
    is_share_model_evaluation_index: false,
    algorithm_type: EnumAlgorithmProjectType.TREE_VERTICAL,
    resource_template_type: ResourceTemplateType.LOW,
    worker_role: Role.LEADER,
    role: RoleUppercase.LEADER,
    peer_role: RoleUppercase.FOLLOWER,

    // Tree model
    loss_type: LossType.LOGISTIC,
    learning_rate: 0.3,
    max_iters: 10,
    max_depth: 5,
    l2_regularization: 1,
    max_bins: 33,
    num_parallel: 5,
    validation_data_path: '',

    // Train info
    label: 'label',
    // ignore_fields: '',

    // NN model
    algorithm: { algorithmId: undefined, algorithmProjectId: undefined, config: [], path: [] },
    save_checkpoint_steps: 1000,
    save_checkpoint_secs: 600,
    epoch_num: 1,
    code_tar: {},
    code_key: '',
    ps_replicas: '1',
    master_replicas: '1',
    worker_replicas: '1',
    batch_size: '',
    shuffle_data_block: '',
    load_checkpoint_filename: '',
    load_checkpoint_filename_with_path: '',
    checkpoint_path: '',
    sparse_estimator: '',
    load_checkpoint_from: '',

    // resource
    master_cpu: '',
    master_mem: '',
    ps_cpu: '',
    ps_mem: '',
    worker_cpu: '16m',
    worker_mem: '64m',
    ps_num: 1,
    worker_num: 1,

    // temp
    data_source: '',
    data_path: '',
    file_ext: '.data',
    file_type: 'tfrecord',
    load_model_name: '',
    enable_packing: '1',
    ignore_fields: '',
    cat_fields: '',
    verify_example_ids: '',
    use_streaming: '',
    no_data: '',
    verbosity: '1',
  },
});

export const evaluationModelForm = atom({
  key: 'EvaluationModelForm',
  default: {
    project_id: undefined,
    report_name: '',
    comment: '',
    dataset_id: undefined,
    dataset_name: '',
    targetList: [
      {
        model_set_id: undefined,
        model_id: undefined,
      },
    ],
    mode: 'eval',
    is_share: false,
    image: '',
    num_partitions: '',
    resource_template_type: ResourceTemplateType.LOW,
    worker_role: Role.LEADER,
    role: RoleUppercase.LEADER,
    peer_role: RoleUppercase.FOLLOWER,

    // Tree model
    loss_type: LossType.LOGISTIC,
    learning_rate: 0.3,
    max_iters: 10,
    max_depth: 5,
    l2_regularization: 1,
    max_bins: 33,
    num_parallel: 5,
    validation_data_path: '',

    // Train info
    label: 'label',
    // ignore_fields: '',

    // NN model
    save_checkpoint_steps: 1000,
    save_checkpoint_secs: 600,
    epoch_num: 1,
    code_tar: {},
    code_key: '',
    ps_replicas: '1',
    master_replicas: '1',
    worker_replicas: '1',
    batch_size: '',
    shuffle_data_block: '',
    load_checkpoint_filename: '',
    load_checkpoint_filename_with_path: '',
    checkpoint_path: '',
    sparse_estimator: '',
    load_checkpoint_from: '',

    // resource
    master_cpu: '',
    master_mem: '',
    ps_cpu: '',
    ps_mem: '',
    worker_cpu: '16m',
    worker_mem: '64m',
    ps_num: 1,
    worker_num: 1,

    // temp
    data_source: '',
    data_path: '',
    file_ext: '.data',
    file_type: 'tfrecord',
    load_model_name: '',
    enable_packing: '1',
    ignore_fields: '',
    cat_fields: '',
    verify_example_ids: '',
    use_streaming: '',
    no_data: '',
    verbosity: '1',
  },
});

export const offlinePredictionModelForm = atom({
  key: 'OfflinePredictionModelForm',
  default: {
    project_id: undefined,
    name: '',
    comment: '',
    dataset_id: undefined,
    dataset_name: '',
    model_set: {
      model_set_id: undefined,
      model_id: undefined,
    },
    mode: 'eval',
    image: '',
    num_partitions: '',
    resource_template_type: ResourceTemplateType.LOW,
    worker_role: Role.LEADER,
    role: RoleUppercase.LEADER,
    peer_role: RoleUppercase.FOLLOWER,

    // Train info
    label: 'label',
    // ignore_fields: '',

    // NN model
    save_checkpoint_steps: 1000,
    save_checkpoint_secs: 600,
    epoch_num: 1,
    code_tar: {},
    code_key: '',
    ps_replicas: '1',
    master_replicas: '1',
    worker_replicas: '1',
    batch_size: '',
    shuffle_data_block: '',
    load_checkpoint_filename: '',
    load_checkpoint_filename_with_path: '',
    checkpoint_path: '',
    sparse_estimator: '',
    load_checkpoint_from: '',

    // resource
    master_cpu: '',
    master_mem: '',
    ps_cpu: '',
    ps_mem: '',
    worker_cpu: '16m',
    worker_mem: '64m',
    ps_num: 1,
    worker_num: 1,

    // temp
    data_source: '',
    data_path: '',
    file_ext: '.data',
    file_type: 'tfrecord',
    load_model_name: '',
    enable_packing: '1',
    ignore_fields: '',
    cat_fields: '',
    verify_example_ids: '',
    use_streaming: '',
    no_data: '',
    verbosity: '1',
  },
});

export const algorithmlForm = atom({
  key: 'AlgorithmlForm',
  default: {
    project_id: undefined,
    name: '',
    comment: '',
    algorithm_type: undefined,
    federation_type: FederationType.CROSS_SAMPLE,

    import_type: UploadType.PATH,
    import_type_label: UploadType.PATH,
    import_type_no_label: UploadType.PATH,
  },
});
