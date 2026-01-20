/* istanbul ignore file */
import {
  DataJobBackEndType,
  DatasetJobListItem,
  DatasetJobState,
  DatasetJobType,
  DatasetKind,
  DatasetKindBackEndType,
  DatasetKindLabel,
  DatasetStateFront,
  DataBatchV2,
  DatasetJobStage,
  DatasetRawPublishStatus,
  Dataset,
  DatasetProcessedAuthStatus,
  DatasetProcessedMyAuthStatus,
  DatasetJob,
} from 'typings/dataset';
import { TableColumnProps } from '@arco-design/web-react';
import { FilterOp } from 'typings/filter';
import { expression2Filter, operationMap } from 'shared/filter';
import { Tag } from 'typings/workflow';

type TableFilterConfig = Pick<TableColumnProps, 'filters' | 'onFilter'>;

export const datasetPageTitles = {
  [DatasetKindLabel.RAW]: '原始数据集',
  [DatasetKindLabel.PROCESSED]: '结果数据集',
  undefined: '未知数据集',
};

export const datasetKindLabelValueMap = {
  [DatasetKindLabel.RAW]: DatasetKind.RAW,
  [DatasetKindLabel.PROCESSED]: DatasetKind.PROCESSED,
  [DatasetKind.RAW]: DatasetKindLabel.RAW,
  [DatasetKind.PROCESSED]: DatasetKindLabel.PROCESSED,
};

export const DataJobBackEndTypeToLabelMap = {
  [DataJobBackEndType.RSA_PSI_DATA_JOIN]: 'RSA-PSI 求交',
  [DataJobBackEndType.LIGHT_CLIENT_RSA_PSI_DATA_JOIN]: 'LIGHT_CLIENT_RSA_PSI数据求交',
  [DataJobBackEndType.LIGHT_CLIENT_OT_PSI_DATA_JOIN]: 'LIGHT_CLIENT_OT_PSI数据求交',
  [DataJobBackEndType.OT_PSI_DATA_JOIN]: 'OT-PSI数据求交',
  [DataJobBackEndType.DATA_JOIN]: '数据求交',
  [DataJobBackEndType.DATA_ALIGNMENT]: '数据对齐',
  [DataJobBackEndType.IMPORT_SOURCE]: '数据导入',
  [DataJobBackEndType.EXPORT]: '导出',
  [DataJobBackEndType.HASH_DATA_JOIN]: '哈希求交',
  [DataJobBackEndType.ANALYZER]: '数据探查',
};

export function isDataJoin(kind?: DataJobBackEndType) {
  if (!kind) return false;
  return [
    DataJobBackEndType.RSA_PSI_DATA_JOIN,
    DataJobBackEndType.LIGHT_CLIENT_RSA_PSI_DATA_JOIN,
    DataJobBackEndType.OT_PSI_DATA_JOIN,
    DataJobBackEndType.DATA_JOIN,
    DataJobBackEndType.HASH_DATA_JOIN,
  ].includes(kind);
}
export function isDataImport(kind?: DataJobBackEndType) {
  if (!kind) return false;
  return [DataJobBackEndType.IMPORT_SOURCE].includes(kind);
}
export function isDataExport(kind?: DataJobBackEndType) {
  if (!kind) return false;
  return [DataJobBackEndType.EXPORT].includes(kind);
}
export function isDataAlignment(kind?: DataJobBackEndType) {
  if (!kind) return false;
  return [DataJobBackEndType.DATA_ALIGNMENT].includes(kind);
}
export function isDataAnalyzer(kind?: DataJobBackEndType) {
  if (!kind) return false;
  return [DataJobBackEndType.ANALYZER].includes(kind);
}

export function isDataLightClient(kind?: DataJobBackEndType) {
  if (!kind) return false;
  return [DataJobBackEndType.LIGHT_CLIENT_RSA_PSI_DATA_JOIN].includes(kind);
}

export function isDataOtPsiJoin(kind?: DataJobBackEndType) {
  if (!kind) return false;
  return [DataJobBackEndType.OT_PSI_DATA_JOIN].includes(kind);
}

export function isDataHashJoin(kind?: DataJobBackEndType) {
  if (!kind) return false;
  return [DataJobBackEndType.HASH_DATA_JOIN].includes(kind);
}

export const datasetJobTypeOptions = [
  {
    label: '求交',
    value: DatasetJobType.JOIN,
  },
  {
    label: '对齐',
    value: DatasetJobType.ALIGNMENT,
  },
  {
    label: '导入',
    value: DatasetJobType.IMPORT,
  },
  {
    label: '导出',
    value: DatasetJobType.EXPORT,
  },
  {
    label: '数据探查',
    value: DatasetJobType.ANALYZER,
  },
];

export const datasetJobStateOptions = [
  {
    label: '待运行',
    value: DatasetJobState.PENDING,
  },
  {
    label: '运行中',
    value: DatasetJobState.RUNNING,
  },
  {
    label: '成功',
    value: DatasetJobState.SUCCEEDED,
  },
  {
    label: '失败',
    value: DatasetJobState.FAILED,
  },
  {
    label: '已停止',
    value: DatasetJobState.STOPPED,
  },
];

export const datasetJobTypeFilters: TableFilterConfig = {
  filters: datasetJobTypeOptions.map((item) => ({
    text: item.label,
    value: item.value,
  })),
  onFilter: (value: string, record: DatasetJobListItem) => {
    switch (value) {
      case DatasetJobType.JOIN:
        return isDataJoin(record.kind);
      case DatasetJobType.ALIGNMENT:
        return [DataJobBackEndType.DATA_ALIGNMENT].includes(record.kind);
      case DatasetJobType.IMPORT:
        return [DataJobBackEndType.IMPORT_SOURCE].includes(record.kind);
      case DatasetJobType.EXPORT:
        return [DataJobBackEndType.EXPORT].includes(record.kind);
      case DatasetJobType.ANALYZER:
        return [DataJobBackEndType.ANALYZER].includes(record.kind);
      default:
        return false;
    }
  },
};

export const datasetJobStateFilters: TableFilterConfig = {
  filters: datasetJobStateOptions
    .filter((opt) => opt.value !== DatasetJobState.PENDING)
    .map((item) => ({
      text: item.label,
      value: item.value,
    })),
  onFilter: (value: string, record: DatasetJobListItem) => {
    if (value === DatasetJobState.RUNNING) {
      return [DatasetJobState.PENDING, DatasetJobState.RUNNING].includes(record.state);
    }
    return value === record.state;
  },
};

export const FILTER_DATA_BATCH_OPERATOR_MAPPER = {
  state: FilterOp.IN,
};

export const dataBatchStateFilters: TableFilterConfig = {
  filters: [
    {
      text: '待处理',
      value: DatasetStateFront.PENDING,
    },
    {
      text: '处理中',
      value: DatasetStateFront.PROCESSING,
    },
    {
      text: '可用',
      value: DatasetStateFront.SUCCEEDED,
    },
    {
      text: '处理失败',
      value: DatasetStateFront.FAILED,
    },
    // {
    //   text: '删除中',
    //   value: DatasetStateFront.DELETING,
    // },
  ],
  onFilter: (value: string, record: DataBatchV2) => {
    return value === record.state;
  },
};

export enum CREDITS_LIMITS {
  MIN = 100,
  MAX = 10000,
}

export const NO_CATEGORY = '未分类';

export const TAG_MAPPER = {
  [Tag.RESOURCE_ALLOCATION]: '资源配置',
  [Tag.INPUT_PARAM]: '输入参数',
  [Tag.INPUT_PATH]: '输入路径',
  [Tag.OUTPUT_PATH]: '输出路径',
  [Tag.OPERATING_PARAM]: '运行参数',
  [Tag.SYSTEM_PARAM]: '系统变量',
};

export enum DatasetJobTypeFront {
  RAW = 'RAW',
  PROCESSED = 'PROCESSED',
  IMPORT = 'IMPORT',
  EXPORTED = 'EXPORTED',
}

export const DATA_JOB_TYPE_MAPPER = {
  [DatasetJobTypeFront.IMPORT]: [DatasetKindBackEndType.SOURCE],
  [DatasetJobTypeFront.RAW]: [DatasetKindBackEndType.RAW],
  [DatasetJobTypeFront.EXPORTED]: [DatasetKindBackEndType.EXPORTED],
  [DatasetJobTypeFront.PROCESSED]: [DatasetKindBackEndType.PROCESSED],
};

/**
 * check the originType form back-end is belonged to target type or not
 * @param originType
 * @param targetType
 */
export function dataJobTypeCheck(
  originType: DatasetKindBackEndType,
  targetType: DatasetJobTypeFront,
): boolean {
  if (!originType || !DATA_JOB_TYPE_MAPPER[targetType]) {
    return false;
  }
  return DATA_JOB_TYPE_MAPPER[targetType].includes(originType);
}

/**
 * generate an expression from filter object
 * @param filter
 * @param filterOpMapper
 */
export function filterExpressionGenerator(
  filter: { [filed: string]: any },
  filterOpMapper: { [filed: string]: FilterOp },
) {
  const filterPairStringArray = [];
  const keys = Object.keys(filter);
  if (!keys.length) {
    return '';
  }
  for (let i = 0; i < keys.length; i++) {
    const key = keys[i];
    const val = filter[key];
    if (typeof val !== 'boolean' && !val && val !== 0) {
      continue;
    }
    const finalVal = JSON.stringify(val);
    const op = filterOpMapper[key];
    op && filterPairStringArray.push(`(${key}${operationMap(op)}${finalVal})`);
  }
  switch (filterPairStringArray.length) {
    case 0:
      return '';
    case 1:
      return filterPairStringArray[0];
    default:
      return `(and${filterPairStringArray.join('')})`;
  }
}

/**
 * get sortValue form urlState
 * @param urlState
 * @param key
 */
export function getSortOrder(urlState: any, key: string) {
  const order = urlState.order_by?.split(' ') || [];
  let res: 'ascend' | 'descend' | undefined = undefined;
  const [keyword, value] = order;
  if (keyword === key) {
    switch (value) {
      case 'asc':
        res = 'ascend';
        break;
      case 'desc':
        res = 'descend';
        break;
      default:
        break;
    }
  }
  return res;
}

export function getPublishState(filter?: string) {
  if (!filter) {
    return undefined;
  }
  return expression2Filter(filter).publish_frontend_state;
}

export const FILTER_OPERATOR_MAPPER = {
  dataset_format: FilterOp.IN,
  publish_frontend_state: FilterOp.EQUAL,
  auth_status: FilterOp.IN,
  name: FilterOp.CONTAIN,
  project_id: FilterOp.EQUAL,
  dataset_kind: FilterOp.EQUAL,
  format: FilterOp.IN,
  participant_id: FilterOp.IN,
  uuid: FilterOp.EQUAL,
  dataset_type: FilterOp.EQUAL,
};

export const FILTER_DATA_JOB_OPERATOR_MAPPER = {
  coordinator_id: FilterOp.IN,
  kind: FilterOp.IN,
  state: FilterOp.IN,
  name: FilterOp.CONTAIN,
};

export const JOB_FRONT_TYPE_TO_BACK_TYPE_MAPPER = {
  [DatasetJobType.JOIN]: [
    DataJobBackEndType.RSA_PSI_DATA_JOIN,
    DataJobBackEndType.LIGHT_CLIENT_RSA_PSI_DATA_JOIN,
    DataJobBackEndType.OT_PSI_DATA_JOIN,
    DataJobBackEndType.DATA_JOIN,
    DataJobBackEndType.HASH_DATA_JOIN,
  ],
  [DatasetJobType.IMPORT]: [DataJobBackEndType.IMPORT_SOURCE],
  [DatasetJobType.EXPORT]: [DataJobBackEndType.EXPORT],
  [DatasetJobType.ALIGNMENT]: [DataJobBackEndType.DATA_ALIGNMENT],
  [DatasetJobType.ANALYZER]: [DataJobBackEndType.ANALYZER],
};

export function getJobKindByFilter(kindList?: DatasetJobType[]) {
  if (!kindList || !kindList.length) {
    return;
  }
  return kindList.reduce((pre, cur) => {
    return pre.concat(JOB_FRONT_TYPE_TO_BACK_TYPE_MAPPER[cur]);
  }, [] as DataJobBackEndType[]);
}

export function getJobStateByFilter(stateList?: DatasetJobState[]) {
  if (!stateList || !stateList.length) {
    return;
  }
  const runningFlag = stateList.includes(DatasetJobState.RUNNING);
  const pendingFlag = stateList.includes(DatasetJobState.PENDING);
  const spliceIndex = pendingFlag
    ? stateList.findIndex((item) => item === DatasetJobState.PENDING)
    : stateList.length;
  pendingFlag && !runningFlag && stateList.splice(spliceIndex, 1);
  runningFlag && !pendingFlag && stateList.push(DatasetJobState.PENDING);
  return stateList;
}

export const VARIABLE_TIPS_MAPPER: { [prop: string]: string } = {
  num_partitions: '数据分片的数量，各方需保持一致',
  part_num: '数据分片的数量，各方需保持一致',
  replicas: '求交worker数量，各方需保持一致',
  part_key: '用来当作求交列的列名',
};

export const SYNCHRONIZATION_VARIABLE = {
  NUM_PARTITIONS: 'num_partitions',
  PART_NUM: 'part_num',
  REPLICAS: 'replicas',
};

export function isDatasetJobStagePending(datasetJobStage?: DatasetJobStage) {
  if (!datasetJobStage) return false;
  return [DatasetJobState.PENDING, DatasetJobState.RUNNING].includes(datasetJobStage?.state);
}

export function isDatasetJobStageFailed(datasetJobStage?: DatasetJobStage) {
  if (!datasetJobStage) return false;
  return [DatasetJobState.FAILED, DatasetJobState.STOPPED].includes(datasetJobStage?.state);
}

export function isDatasetJobStageSuccess(datasetJobStage?: DatasetJobStage) {
  if (!datasetJobStage) return false;
  return [DatasetJobState.SUCCEEDED].includes(datasetJobStage?.state);
}

export function isDatasetTicket(data: Dataset) {
  return [DatasetRawPublishStatus.TICKET_PENDING, DatasetRawPublishStatus.TICKET_DECLINED].includes(
    data.publish_frontend_state,
  );
}

export function isDatasetPublished(data: Dataset) {
  return data.publish_frontend_state === DatasetRawPublishStatus.PUBLISHED;
}

export function isFrontendAuthorized(data: Dataset) {
  return data.local_auth_status === DatasetProcessedMyAuthStatus.AUTHORIZED;
}

export const RawPublishStatusOptions = [
  {
    status: DatasetRawPublishStatus.UNPUBLISHED,
    text: '未发布',
    color: '#165DFF',
    percent: 25,
  },
  {
    status: DatasetRawPublishStatus.TICKET_PENDING,
    text: '待审批',
    color: '#165DFF',
    percent: 70,
  },
  {
    status: DatasetRawPublishStatus.TICKET_PENDING,
    text: '审批拒绝',
    color: '#FA9600',
    percent: 70,
  },
  {
    status: DatasetRawPublishStatus.PUBLISHED,
    text: '已发布',
    color: '#165DFF',
    percent: 100,
  },
];

export const RawAuthStatusOptions = [
  {
    status: DatasetProcessedAuthStatus.TICKET_PENDING,
    text: '待审批',
    color: '#165DFF',
    percent: 25,
  },
  {
    status: DatasetProcessedAuthStatus.TICKET_PENDING,
    text: '审批拒绝',
    color: '#FA9600',
    percent: 50,
  },
  {
    status: DatasetProcessedAuthStatus.AUTH_PENDING,
    text: '待授权',
    color: '#165DFF',
    percent: 100,
  },

  {
    status: DatasetProcessedAuthStatus.AUTH_APPROVED,
    text: '授权通过',
    color: '#00B42A',
    percent: 100,
  },
];

export function isSingleParams(kind?: DataJobBackEndType) {
  if (!kind) {
    return false;
  }
  return [
    DataJobBackEndType.EXPORT,
    DataJobBackEndType.IMPORT_SOURCE,
    DataJobBackEndType.ANALYZER,
    DataJobBackEndType.LIGHT_CLIENT_OT_PSI_DATA_JOIN,
    DataJobBackEndType.LIGHT_CLIENT_RSA_PSI_DATA_JOIN,
  ].includes(kind);
}

export enum CronType {
  DAY = 'DAY',
  HOUR = 'HOUR',
}

export const cronTypeOptions = [
  {
    value: CronType.DAY,
    label: '每天',
    warnTip: '天级导入只会读取文件夹格式为 YYYYMMDD （如20220101） 下的数据。',
  },
  {
    value: CronType.HOUR,
    label: '每小时',
    warnTip: '小时级导入只会读取文件夹格式为 YYYYMMDD-HH（如20220101-12） 下的数据。',
  },
];

export function isHoursCronJoin(datasetJob?: DatasetJob) {
  return datasetJob?.time_range?.hours === 1;
}
