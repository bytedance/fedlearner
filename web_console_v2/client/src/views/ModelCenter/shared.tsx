import React from 'react';
import { cloneDeep, flattenDeep } from 'lodash-es';

import { workflowStateFilterParamToStateTextMap } from 'shared/workflow';

import { Message, Modal, TableColumnProps } from '@arco-design/web-react';
import { ActionItem, StateTypes } from 'components/StateIndicator';
import { WorkflowConfig, WorkflowState, WorkflowStateFilterParam, Tag } from 'typings/workflow';
import { Variable, VariableWidgetSchema } from 'typings/variable';
import { ItemProps } from 'components/ConfigForm';
import { PlusBold } from 'components/IconPark';
import { FilterOp } from 'typings/filter';

import {
  FederalType,
  ModelJobGroup,
  ModelJobRole,
  TrainRoleType,
  ModelJob,
  AlgorithmType,
  LossType,
  ModelJobVariable,
  ModelGroupStatus,
  ModelJobStatus,
  ModelJobAuthStatus,
} from 'typings/modelCenter';

import { ModelEvaluationModuleType } from './routes';
import { EnumAlgorithmProjectType } from 'typings/algorithm';
import { VariableComponent } from 'typings/variable';
import { processVariableTypedValue, stringifyVariableValue } from 'shared/formSchema';
import { Participant } from 'typings/participant';
import { deleteJob_new } from 'services/modelCenter';

import styles from './shared.module.less';

enum FiltersFields {
  ALGORITHM_TYPE = 'algorithm_type',
  STATUS = 'status',
  ROLE = 'role',
}

const TIP_MAPPER: Record<string, string> = {
  image_version: '镜像版本',
  learning_rate: '使用损失函数的梯度调整网络权重的超参数，​ 推荐区间（0.01-1]',
  enable_packing: '提高计算效率，true 为优化，false 为不优化。',
  ignore_fields: '不参与训练的字段',
  cat_fields: '类别变量字段，训练中会特别处理',
  send_scores_to_follower: '是否将预测值发送至follower侧，fasle代表否，ture代表是',
  send_metrics_to_follower: '是否将指标发送至follower侧，fasle代表否，ture代表是',
  verify_example_ids:
    '是否检验example_ids，一般情况下训练数据有example_ids，fasle代表否，ture代表是',
  no_data: '针对标签方没有特征的预测场景，fasle代表有特征，ture代表无特征。',
  label_field: '用于指定label',
  load_model_name: '评估和预测时，根据用户选择的模型，确定该字段的值。',
  shuffle_data_block: '打乱数据顺序，增加随机性，提高模型泛化能力',
  save_checkpoint_secs: '模型多少秒保存一次',
  save_checkpoint_steps: '模型多少step保存一次',
  load_checkpoint_filename: '加载文件名，用于评估和预测时选择模型',
  load_checkpoint_filename_with_path: '加载文件路径，用于更细粒度的控制到底选择哪个时间点的模型',
  sparse_estimator:
    '是否使用火山引擎的SparseEstimator，由火山引擎侧工程师判定，客户侧默认都为false',
  steps_per_sync: '用于指定参数同步的频率，比如step间隔为10，也就是训练10个batch同步一次参数。',
  feature_importance: '数值越高，表示该特征对模型的影响越大',
  metric_is_publish: '开启后，将与合作伙伴共享本次训练指标',
};

export const LABEL_MAPPER: Record<string, string> = {
  image: '镜像',
  data_source: '数据源',
  epoch_num: 'epoch_num',
  verbosity: '日志输出等级',
  shuffle_data_block: '是否打乱顺序',
  save_checkpoint_steps: '保存备份间隔步数',
  save_checkpoint_secs: '保存备份间隔秒数',
  load_checkpoint_filename: '加载文件名',
  load_checkpoint_filename_with_path: '加载文件路径',
  sparse_estimator: 'sparse_estimator',
  load_model_name: '加载模型名称',
  data_path: '数据源',
  steps_per_sync: '参数同步 step 间隔',

  learning_rate: '学习率',
  max_iters: '迭代数',
  max_depth: '最大深度',
  l2_regularization: 'L2惩罚系数',
  max_bins: '最大分箱数量',
  num_parallel: ' 线程池大小',
  file_ext: '文件扩展名',
  file_type: '文件类型',
  enable_packing: '是否优化',
  ignore_fields: '忽略字段',
  cat_fields: '类型变量字段',
  send_metrics_to_follower: '是否将指标发送至 follower',
  send_scores_to_follower: '是否将预测值发送至 follower',
  verify_example_ids: '是否检验 example_ids',
  no_data: '标签方是否无特征',
  image_version: '镜像版本号',
  num_partitions: 'num_partitions',
  validation_data_path: '验证数据集地址',
  label_field: '标签字段',
  load_model_path: '加载模型路径',
};

export const MODEL_JOB_STATUE_TEXT_MAPPER: Record<ModelJobStatus, string> = {
  [ModelJobStatus.PENDING]: '未配置',
  [ModelJobStatus.CONFIGURED]: '配置成功',
  [ModelJobStatus.ERROR]: '错误',
  [ModelJobStatus.RUNNING]: '运行中',
  [ModelJobStatus.SUCCEEDED]: '成功',
  [ModelJobStatus.STOPPED]: '已停止',
  [ModelJobStatus.FAILED]: '失败',
  [ModelJobStatus.UNKNOWN]: '未知状态',
};

export type TableFiltersValue = Partial<Record<FiltersFields, string[]>>;

export type ColumnsGetterOptions = {
  onDeleteClick?: any;
  onRestartClick?: any;
  onStopClick?: any;
  onLogClick?: any;
  onReportNameClick?: any;

  module?: ModelEvaluationModuleType;
  nameFieldText?: string;
  withoutActions?: boolean;
  isRestartLoading?: boolean;
  isHideAllActionList?: boolean;
  filterDropdownValues?: TableFiltersValue;
  participantList?: Participant[];
  myPureDomainName?: string;
};

export function getModelJobState(
  state: ModelJob['state'],
  options?: ColumnsGetterOptions,
): { type: StateTypes; text: string; actionList?: ActionItem[] } {
  switch (state) {
    case WorkflowState.PARTICIPANT_CONFIGURING:
      return {
        text:
          workflowStateFilterParamToStateTextMap[WorkflowStateFilterParam.PARTICIPANT_CONFIGURING],
        type: 'gold',
      };

    case WorkflowState.PENDING_ACCEPT:
      return {
        text: workflowStateFilterParamToStateTextMap[WorkflowStateFilterParam.PENDING_ACCEPT],
        type: 'warning',
      };

    case WorkflowState.WARMUP_UNDERHOOD:
      return {
        text: workflowStateFilterParamToStateTextMap[WorkflowStateFilterParam.WARMUP_UNDERHOOD],
        type: 'warning',
      };

    case WorkflowState.PREPARE_RUN:
      return {
        text: workflowStateFilterParamToStateTextMap[WorkflowStateFilterParam.PREPARE_RUN],
        type: 'warning',
      };

    case WorkflowState.READY_TO_RUN:
      return {
        text: workflowStateFilterParamToStateTextMap[WorkflowStateFilterParam.READY_TO_RUN],
        type: 'lime',
      };

    case WorkflowState.RUNNING:
      return {
        text: workflowStateFilterParamToStateTextMap[WorkflowStateFilterParam.RUNNING],
        type: 'processing',
      };

    case WorkflowState.PREPARE_STOP:
      return {
        text: workflowStateFilterParamToStateTextMap[WorkflowStateFilterParam.PREPARE_STOP],
        type: 'error',
      };

    case WorkflowState.STOPPED:
      return {
        text: workflowStateFilterParamToStateTextMap[WorkflowStateFilterParam.STOPPED],
        type: 'error',
      };

    case WorkflowState.COMPLETED:
      return {
        text: workflowStateFilterParamToStateTextMap[WorkflowStateFilterParam.COMPLETED],
        type: 'success',
      };

    case WorkflowState.FAILED:
      return {
        text: workflowStateFilterParamToStateTextMap[WorkflowStateFilterParam.FAILED],
        type: 'error',
        actionList: options?.isHideAllActionList
          ? []
          : [
              {
                label: '查看日志',
                onClick: options?.onLogClick,
              },
              {
                label: '重新发起',
                onClick: options?.onRestartClick,
                isLoading: !!options?.isRestartLoading,
              },
            ],
      };

    case WorkflowState.INVALID:
      return {
        text: workflowStateFilterParamToStateTextMap[WorkflowStateFilterParam.INVALID],
        type: 'default',
      };
    case WorkflowState.UNKNOWN:
    default:
      return {
        text: workflowStateFilterParamToStateTextMap[WorkflowStateFilterParam.UNKNOWN],
        type: 'default',
      };
  }
}

export function getModelJobStatus(
  status: ModelJobStatus,
  options?: ColumnsGetterOptions,
): { type: StateTypes; text: string; actionList?: ActionItem[] } {
  const modelJobStatusText = MODEL_JOB_STATUE_TEXT_MAPPER[status];
  switch (status) {
    case ModelJobStatus.PENDING:
      return {
        text: modelJobStatusText,
        type: 'default',
      };
    case ModelJobStatus.CONFIGURED:
      return {
        text: modelJobStatusText,
        type: 'success',
      };
    case ModelJobStatus.ERROR:
      return {
        text: modelJobStatusText,
        type: 'error',
      };
    case ModelJobStatus.RUNNING:
      return {
        text: modelJobStatusText,
        type: 'processing',
      };
    case ModelJobStatus.STOPPED:
      return {
        text: modelJobStatusText,
        type: 'error',
      };
    case ModelJobStatus.SUCCEEDED:
      return {
        text: modelJobStatusText,
        type: 'success',
      };
    case ModelJobStatus.FAILED:
      return {
        text: modelJobStatusText,
        type: 'error',
        actionList: options?.isHideAllActionList
          ? []
          : [
              {
                label: '查看日志',
                onClick: options?.onLogClick,
              },
              {
                label: '重新发起',
                onClick: options?.onRestartClick,
                isLoading: !!options?.isRestartLoading,
              },
            ],
      };
    case ModelJobStatus.UNKNOWN:
    default:
      return {
        text: MODEL_JOB_STATUE_TEXT_MAPPER[ModelJobStatus.UNKNOWN],
        type: 'default',
      };
  }
}

export function getAlgorithmTypeText(val: ModelJob['algorithm_type']) {
  const [, type] = (val ?? '').split('_');
  if (!type) {
    return;
  }

  switch (type.toLowerCase()) {
    case 'vertical':
      return '纵向联邦';
    case 'horizontal':
      return '横向联邦';
    default:
      return val;
  }
}

export const Avatar: React.FC = () => {
  return <div className={styles.avatar_container} />;
};

export async function dangerConfirmWrapper(
  title: string,
  content: string,
  okText: string,
  onConfirm: () => Promise<any>,
  onCancel?: () => void,
) {
  Modal.confirm({
    className: 'custom-modal',
    title,
    content,
    okText,
    okButtonProps: {
      status: 'danger',
    },
    cancelText: '取消',
    onConfirm: onConfirm,
    onCancel,
  });
}

export const lossTypeOptions = [
  {
    value: LossType.LOGISTIC,
    label: 'logistic',
    tip: '用于分类任务',
  },
  {
    value: LossType.MSE,
    label: 'mse',
    tip: '用于回归任务',
  },
];

export const algorithmTypeOptions = [
  {
    label: '纵向联邦-树模型',
    value: EnumAlgorithmProjectType.TREE_VERTICAL,
  },
  {
    label: '横向联邦-NN模型',
    value: EnumAlgorithmProjectType.NN_HORIZONTAL,
  },
  {
    label: '纵向联邦-NN模型',
    value: EnumAlgorithmProjectType.NN_VERTICAL,
  },
];

export const federalTypeOptions = [
  {
    value: FederalType.VERTICAL,
    label: '纵向联邦',
  },
  {
    value: FederalType.HORIZONTAL,
    label: '横向联邦',
  },
];

export const trainRoleTypeOptions = [
  {
    value: TrainRoleType.LABEL,
    label: '标签方',
  },
  {
    value: TrainRoleType.FEATURE,
    label: '特征方',
  },
];
export const treeBaseConfigList: ItemProps[] = [
  {
    field: 'learning_rate',
    label: '学习率',
    tip: '使用损失函数的梯度调整网络权重的超参数，​ 推荐区间（0.01-1]',
    componentType: VariableComponent.NumberPicker,
    initialValue: 0.3,
  },
  {
    field: 'max_iters',
    label: '迭代数',
    tip: '该模型包含树的数量，推荐区间（5-20）',
    componentType: VariableComponent.NumberPicker,
    initialValue: 10,
  },
  {
    field: 'max_depth',
    label: '最大深度',
    tip: '树模型的最大深度，用来控制过拟合，推荐区间（4-7）',
    componentType: VariableComponent.NumberPicker,
    initialValue: 5,
  },
  {
    field: 'l2_regularization',
    label: 'L2惩罚系数',
    tip: '对节点预测值的惩罚系数，推荐区间（0.01-10）',
    componentType: VariableComponent.NumberPicker,
    initialValue: 1,
  },
  {
    field: 'max_bins',
    label: '最大分箱数量',
    tip: '离散化连续变量，可以减少数据稀疏度，一般不需要调整',
    componentType: VariableComponent.NumberPicker,
    initialValue: 33,
  },
  {
    field: 'num_parallel',
    label: '线程池大小',
    tip: '建议与CPU核数接近',
    componentType: VariableComponent.NumberPicker,
    initialValue: 5,
  },
];
export const nnBaseConfigList: ItemProps[] = [
  {
    field: 'epoch_num',
    label: 'epoch_num',
    tip: '指一次完整模型训练需要多少次Epoch，一次Epoch是指将全部训练样本训练一遍',
    componentType: VariableComponent.NumberPicker,
    initialValue: 1,
  },
  {
    field: 'verbosity',
    label: '日志输出等级',
    tip: '有 0、1、2、3 四种等级，等级越大日志输出的信息越多',
    componentType: VariableComponent.NumberPicker,
    initialValue: 1,
  },
];

export const TREE_BASE_CONFIG_FIELD_LIST = treeBaseConfigList.map((item) => item.field) as string[];
export const NN_BASE_CONFIG_FIELD_LIST = nnBaseConfigList.map((item) => item.field) as string[];

export const NOT_TREE_ADVANCE_CONFIG_FIELD_LIST = [
  ...TREE_BASE_CONFIG_FIELD_LIST,
  'loss_type',
  'role',
  'worker_cpu',
  'worker_mem',
  'mode',
  'algorithm',
];
export const NOT_NN_ADVANCE_CONFIG_FIELD_LIST = [
  ...NN_BASE_CONFIG_FIELD_LIST,
  'role',
  'worker_cpu',
  'worker_mem',
  'worker_replicas',
  'master_cpu',
  'master_mem',
  'master_replicas',
  'ps_cpu',
  'ps_mem',
  'ps_replicas',
  'mode',
  'algorithm',
];

export function getAdvanceConfigListByDefinition(variables: Variable[], isNN = false): ItemProps[] {
  const blockList = isNN ? NOT_NN_ADVANCE_CONFIG_FIELD_LIST : NOT_TREE_ADVANCE_CONFIG_FIELD_LIST;

  const advanceConfigList: ItemProps[] = [];
  const variableList = flattenDeep(variables);
  variableList.forEach((item) => {
    if (!blockList.includes(item.name) && item.tag === Tag.INPUT_PARAM) {
      let widget_schema: VariableWidgetSchema = {};

      try {
        widget_schema = JSON.parse(item.widget_schema as any);
      } catch (error) {}
      advanceConfigList.push({
        field: item.name,
        label: LABEL_MAPPER?.[item.name] ?? item.name,
        initialValue: item.value,
        tip: widget_schema.tooltip ?? TIP_MAPPER?.[item.name],
      });
    }
  });

  return advanceConfigList;
}
export function getAdvanceConfigList(config: WorkflowConfig, isNN = false) {
  const blockList = isNN ? NOT_NN_ADVANCE_CONFIG_FIELD_LIST : NOT_TREE_ADVANCE_CONFIG_FIELD_LIST;

  const advanceConfigList: ItemProps[] = [];

  const variableList = flattenDeep(
    [config.variables || []].concat((config.job_definitions || []).map((item) => item.variables)),
  );

  variableList.forEach((item) => {
    if (!blockList.includes(item.name)) {
      const labelI18nKey = LABEL_MAPPER[item.name];
      const tipI18nKey = TIP_MAPPER[item.name];
      let widget_schema: VariableWidgetSchema = {};

      try {
        widget_schema = JSON.parse(item.widget_schema as any);
      } catch (error) {}
      advanceConfigList.push({
        field: item.name,
        label: labelI18nKey ?? item.name,
        initialValue: item.value,
        tip: widget_schema.tooltip ?? tipI18nKey,
      });
    }
  });

  return advanceConfigList;
}
export function getConfigInitialValuesByDefinition(
  variables: Variable[],
  list: string[] = [],
  isBlockList = false,
  valuePreset: Record<string, any> = {},
) {
  const variableList = flattenDeep(variables);
  const initialValues: { [key: string]: any } = {};

  variableList.forEach((item) => {
    if (isBlockList) {
      if (!list.includes(item.name)) {
        initialValues[item.name] = item.value ?? valuePreset[item.name];
      }
    } else {
      if (list.includes(item.name)) {
        initialValues[item.name] = item.value ?? valuePreset[item.name];
      }
    }
  });

  return initialValues;
}
export function getConfigInitialValues(
  config: WorkflowConfig,
  list: string[] = [],
  isBlockList = false,
  valuePreset: Record<string, any> = {},
) {
  const variableList = flattenDeep(
    [config?.variables || []].concat((config?.job_definitions || []).map((item) => item.variables)),
  );

  const initialValues: { [key: string]: any } = {};

  variableList.forEach((item) => {
    if (isBlockList) {
      if (!list.includes(item.name)) {
        initialValues[item.name] = item.value ?? valuePreset[item.name];
      }
    } else {
      if (list.includes(item.name)) {
        initialValues[item.name] = item.value ?? valuePreset[item.name];
      }
    }
  });

  return initialValues;
}
export function getTreeBaseConfigInitialValuesByDefinition(variables: Variable[]) {
  return getConfigInitialValuesByDefinition(variables, TREE_BASE_CONFIG_FIELD_LIST, false, {
    learning_rate: 0.3,
    max_iters: 5,
    max_depth: 3,
    l2_regularization: 1.0,
    max_bins: 33,
    num_parallel: 5,
  });
}
export function getNNBaseConfigInitialValuesByDefinition(variables: Variable[]) {
  return getConfigInitialValuesByDefinition(variables, NN_BASE_CONFIG_FIELD_LIST, false, {
    epoch_num: 1,
    verbosity: 1,
  });
}
export function getTreeBaseConfigInitialValues(config: WorkflowConfig) {
  return getConfigInitialValues(config, TREE_BASE_CONFIG_FIELD_LIST, false, {
    learning_rate: 0.3,
    max_iters: 5,
    max_depth: 3,
    l2_regularization: 1.0,
    max_bins: 33,
    num_parallel: 5,
  });
}
export function getTreeAdvanceConfigInitialValues(config: WorkflowConfig) {
  return getConfigInitialValues(config, NOT_TREE_ADVANCE_CONFIG_FIELD_LIST, true, {
    file_ext: '.data',
    file_type: 'tfrecord',
    enable_packing: true,
    send_scores_to_follower: false,
    send_metrics_to_follower: false,
    verify_example_ids: true,
    verbosity: 1,
    no_data: false,
    label_field: 'label',
  });
}

export function getNNBaseConfigInitialValues(config: WorkflowConfig) {
  return getConfigInitialValues(config, NN_BASE_CONFIG_FIELD_LIST, false, {
    epoch_num: 1,
    verbosity: 1,
  });
}
export function getNNAdvanceConfigInitialValues(config: WorkflowConfig) {
  return getConfigInitialValues(config, NOT_NN_ADVANCE_CONFIG_FIELD_LIST, true, {
    shuffle_data_block: true,
    save_checkpoint_secs: 600,
    save_checkpoint_steps: 1000,
    sparse_estimator: false,
    steps_per_sync: 10,
  });
}

export function hydrateWorkflowConfig(
  workflowConfig: WorkflowConfig,
  values: { [key: string]: any },
) {
  const tempConfig = cloneDeep(workflowConfig);

  const keyList = Object.keys(values);

  for (let index = 0; index < keyList.length; index++) {
    const key = keyList[index];

    // send_metrics_to_follower,send_scores_to_follower
    // only empty string will treat as false
    const formValue = ['send_metrics_to_follower', 'send_scores_to_follower'].includes(key)
      ? values[key]
        ? true
        : ''
      : values[key];

    let isBreak = false;

    // variables
    for (let j = 0; j < tempConfig.variables.length; j++) {
      if (tempConfig.variables[j].name === key) {
        tempConfig.variables[j].value = formValue;
        isBreak = true;
        break;
      }
    }
    if (isBreak) {
      continue;
    }

    // job_definitions
    for (let i = 0; i < tempConfig.job_definitions.length; i++) {
      for (let j = 0; j < tempConfig.job_definitions[i].variables.length; j++) {
        if (tempConfig.job_definitions[i].variables[j].name === key) {
          tempConfig.job_definitions[i].variables[j].value = formValue;
          isBreak = true;
          break;
        }
      }
      if (isBreak) {
        break;
      }
    }
  }
  return tempConfig;
}

/**
 * @param variable Variable defintions without any user input value
 * @param values User inputs
 */
export function hydrateModalGlobalConfig(
  variables: Array<ModelJobVariable | Variable>,
  values: { [key: string]: any },
  hasAlgorithmUuid: boolean = true,
): Array<Variable> {
  const tempVariables = cloneDeep(variables);
  const resultVariables = [];
  const keyList = Object.keys(values);

  for (let index = 0; index < keyList.length; index++) {
    const key = keyList[index];
    const formValue = ['send_metrics_to_follower', 'send_scores_to_follower'].includes(key)
      ? values[key]
        ? true
        : ''
      : values[key];

    for (let j = 0; j < tempVariables.length; j++) {
      const newVariable = cloneDeep(tempVariables[j]);
      if (
        newVariable.name === key &&
        (newVariable.tag === Tag.INPUT_PARAM ||
          newVariable.tag === Tag.RESOURCE_ALLOCATION ||
          (newVariable.name === 'algorithm' && !hasAlgorithmUuid))
      ) {
        newVariable.value = formValue;
        stringifyVariableValue(newVariable as Variable);
        processVariableTypedValue(newVariable as Variable);
        if (typeof newVariable.widget_schema === 'object') {
          newVariable.widget_schema = JSON.stringify(newVariable.widget_schema);
        }
        resultVariables.push(newVariable);
        break;
      }
    }
  }
  return resultVariables as Variable[];
}

type TableFilterConfig = Pick<TableColumnProps, 'filters' | 'onFilter'>;

export const algorithmTypeFilters: TableFilterConfig = {
  filters: algorithmTypeOptions.map((item) => ({
    text: item.label,
    value: item.value,
  })),
  onFilter: (value: string, record: any) => {
    return record?.algorithm_type === value;
  },
};

export const roleFilters: TableFilterConfig = {
  filters: [
    {
      text: '本方',
      value: ModelJobRole.COORDINATOR,
    },
    {
      text: '合作伙伴',
      value: ModelJobRole.PARTICIPANT,
    },
  ],
  onFilter: (value: string, record: any) => {
    return record?.role === value;
  },
};

export const stateFilters: TableFilterConfig = {
  filters: [
    WorkflowState.RUNNING,
    WorkflowState.STOPPED,
    WorkflowState.INVALID,
    WorkflowState.COMPLETED,
    WorkflowState.FAILED,
    WorkflowState.PREPARE_RUN,
    WorkflowState.PREPARE_STOP,
    WorkflowState.WARMUP_UNDERHOOD,
    WorkflowState.PENDING_ACCEPT,
    WorkflowState.READY_TO_RUN,
    WorkflowState.PARTICIPANT_CONFIGURING,
    WorkflowState.UNKNOWN,
  ].map((state) => {
    const { text } = getModelJobState(state);
    return { text, value: state };
  }),
  onFilter: (value: string, record: ModelJobGroup | ModelJob) => {
    return (
      (record as ModelJob)?.state === value || (record as ModelJobGroup)?.latest_job_state === value
    );
  },
};

export const statusFilters: TableFilterConfig = {
  filters: [
    ModelJobStatus.PENDING,
    ModelJobStatus.CONFIGURED,
    ModelJobStatus.ERROR,
    ModelJobStatus.RUNNING,
    ModelJobStatus.SUCCEEDED,
    ModelJobStatus.STOPPED,
    ModelJobStatus.FAILED,
    ModelJobStatus.UNKNOWN,
  ].map((status) => {
    return { text: MODEL_JOB_STATUE_TEXT_MAPPER[status], value: status };
  }),
  onFilter: (value: string, record: ModelJob | ModelJobGroup) => {
    return (
      (record as ModelJob)?.status === value ||
      (record as ModelJobGroup)?.latest_job_state === value
    );
  },
};

export const StyledPlusIcon: React.FC = () => {
  return <PlusBold className={styles.plus_icon} />;
};

export function getDataSource(path: string) {
  const regex = /\/data_source\/(.*)$/;
  const matchList = path.match(regex);
  return matchList?.[1] ?? '';
}

export function deleteEvaluationJob(
  projectId: ID,
  job: ModelJob,
  module: ModelEvaluationModuleType,
): Promise<boolean> {
  return new Promise((resolve, reject) => {
    dangerConfirmWrapper(
      `确认要删除「${job.name}」？`,

      module === ModelEvaluationModuleType.Evaluation
        ? '删除后，该评估任务及信息将无法恢复，请谨慎操作'
        : '删除后，该预测任务及信息将无法恢复，请谨慎操作',
      '删除',
      async () => {
        try {
          await deleteJob_new(projectId, job.id);
          Message.success('删除成功');
          resolve(true);
        } catch (e: any) {
          Message.error(e.message);
          reject(e);
        }
      },
      () => {
        resolve(false);
      },
    );
  });
}

export function isTreeAlgorithm(algorithmType: EnumAlgorithmProjectType | AlgorithmType) {
  return [
    EnumAlgorithmProjectType.TREE_HORIZONTAL,
    EnumAlgorithmProjectType.TREE_VERTICAL,
    AlgorithmType.TREE,
  ].includes(algorithmType);
}
export function isNNAlgorithm(algorithmType: EnumAlgorithmProjectType | AlgorithmType) {
  return [
    EnumAlgorithmProjectType.NN_HORIZONTAL,
    EnumAlgorithmProjectType.NN_VERTICAL,
    EnumAlgorithmProjectType.NN_LOCAL,
    AlgorithmType.NN,
  ].includes(algorithmType);
}

export function isOldAlgorithm(algorithmType: EnumAlgorithmProjectType | AlgorithmType) {
  return [AlgorithmType.TREE, AlgorithmType.NN].includes(algorithmType as AlgorithmType);
}
export function isHorizontalAlgorithm(algorithmType: EnumAlgorithmProjectType) {
  return [
    EnumAlgorithmProjectType.TREE_HORIZONTAL,
    EnumAlgorithmProjectType.NN_HORIZONTAL,
  ].includes(algorithmType);
}
export function isVerticalAlgorithm(algorithmType: EnumAlgorithmProjectType) {
  return [EnumAlgorithmProjectType.TREE_VERTICAL, EnumAlgorithmProjectType.NN_VERTICAL].includes(
    algorithmType,
  );
}

export function isVerticalNNAlgorithm(algorithmType: EnumAlgorithmProjectType) {
  return algorithmType === EnumAlgorithmProjectType.NN_VERTICAL;
}

export const checkAlgorithmValueIsEmpty = (
  value: { algorithmProjectId: any; algorithmId: any } | undefined,
  callback: (error?: string) => void,
) => {
  if (
    value &&
    (value.algorithmProjectId || value.algorithmProjectId === 0) &&
    (value.algorithmId || value.algorithmId === 0 || value.algorithmId === null)
  ) {
    return callback();
  }
  return callback('必填项');
};

export enum TRAIN_ROLE {
  LEADER = 'Leader',
  FOLLOWER = 'Follower',
}

export const FILTER_MODEL_TRAIN_OPERATOR_MAPPER = {
  role: FilterOp.IN,
  algorithm_type: FilterOp.IN,
  name: FilterOp.CONTAIN,
  configured: FilterOp.EQUAL,
  //TODO: 'states' support BE filter
};
export const FILTER_MODEL_JOB_OPERATOR_MAPPER = {
  role: FilterOp.IN,
  algorithm_type: FilterOp.IN,
  name: FilterOp.CONTAIN,
  model_job_type: FilterOp.IN,
  status: FilterOp.IN,
  configured: FilterOp.EQUAL,
  auth_status: FilterOp.IN,
};

export const MODEL_GROUP_STATUS_MAPPER: Record<ModelGroupStatus, any> = {
  TICKET_PENDING: {
    status: 'default',
    percent: 30,
    name: '待审批',
  },
  CREATE_PENDING: {
    status: 'default',
    percent: 40,
    name: '创建中',
  },
  CREATE_FAILED: {
    status: 'warning',
    percent: 100,
    name: '创建失败',
  },
  TICKET_DECLINE: {
    status: 'warning',
    percent: 30,
    name: '审批拒绝',
  },
  SELF_AUTH_PENDING: {
    status: 'default',
    percent: 50,
    name: '待我方授权',
  },
  PART_AUTH_PENDING: {
    status: 'default',
    percent: 70,
    name: '待合作伙伴授权',
  },
  ALL_AUTHORIZED: {
    status: 'success',
    percent: 100,
    name: '授权通过',
  },
};

export const AUTH_STATUS_TEXT_MAP: Record<string, string> = {
  PENDING: '待授权',
  AUTHORIZED: '已授权',
  WITHDRAW: '待授权',
};
export function resetAuthInfo(
  participantsMap: Record<string, any> | undefined,
  participantList: Participant[],
  myPureDomainName: string,
) {
  const resultList: any[] = [];
  const keyList = Object.keys(participantsMap || {});
  keyList.forEach((key) => {
    const curParticipant = participantList.find(
      (participant: Participant) => participant?.pure_domain_name === key,
    );
    key !== myPureDomainName &&
      curParticipant &&
      resultList.push({
        name: curParticipant?.name,
        authStatus: participantsMap?.[key].auth_status,
      });
  });
  resultList.sort((a: any, b: any) => {
    return a.name > b.name ? 1 : -1;
  });
  resultList.unshift({
    name: '我方',
    authStatus: participantsMap?.[myPureDomainName]?.auth_status,
  });
  return resultList;
}

export const ALGORITHM_TYPE_LABEL_MAPPER: Record<string, string> = {
  NN_HORIZONTAL: '横向联邦-NN模型',
  NN_VERTICAL: '纵向联邦-NN模型',
  TREE_VERTICAL: '纵向联邦-树模型',
};

export const MODEL_JOB_STATUS_MAPPER: Record<ModelJobAuthStatus, any> = {
  TICKET_PENDING: {
    status: 'default',
    percent: 30,
    name: '待审批',
  },
  CREATE_PENDING: {
    status: 'default',
    percent: 40,
    name: '创建中',
  },
  CREATE_FAILED: {
    status: 'warning',
    percent: 100,
    name: '创建失败',
  },
  TICKET_DECLINE: {
    status: 'warning',
    percent: 30,
    name: '审批拒绝',
  },
  SELF_AUTH_PENDING: {
    status: 'default',
    percent: 50,
    name: '待我方授权',
  },
  PART_AUTH_PENDING: {
    status: 'default',
    percent: 70,
    name: '待合作伙伴授权',
  },
  ALL_AUTHORIZED: {
    status: 'success',
    percent: 100,
    name: '授权通过',
  },
};
