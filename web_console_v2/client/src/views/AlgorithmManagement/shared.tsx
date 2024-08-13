import React from 'react';
import styled from './shared.module.less';
import {
  EnumAlgorithmProjectType,
  EnumAlgorithmProjectSource,
  AlgorithmProject,
  Algorithm,
  AlgorithmReleaseStatus,
} from 'typings/algorithm';
import { deleteAlgorithm, deleteAlgorithmProject, unpublishAlgorithm } from 'services/algorithm';
import { Modal, TableColumnProps } from '@arco-design/web-react';
import { FilterOp } from 'typings/filter';
type TableFilterConfig = Pick<TableColumnProps, 'filters' | 'onFilter'>;

export const AlgorithmProjectTypeText = {
  [EnumAlgorithmProjectType.UNSPECIFIED]: '自定义算法',
  [EnumAlgorithmProjectType.NN_VERTICAL]: '纵向联邦-NN模型',
  [EnumAlgorithmProjectType.NN_LOCAL]: '本地-NN模型',
  [EnumAlgorithmProjectType.TREE_VERTICAL]: '纵向联邦-树模型',
  [EnumAlgorithmProjectType.TREE_HORIZONTAL]: '横向联邦-树模型',
};

export const AlgorithmTypeOptions = [
  {
    label: '自定义算法',
    value: EnumAlgorithmProjectType.UNSPECIFIED,
  },
  // {
  //   label: i18n.t('algorithm_management.label_model_type_nn_local'),
  //   value: EnumAlgorithmProjectType.NN_LOCAL,
  // },
  {
    label: '横向联邦-NN模型',
    value: EnumAlgorithmProjectType.NN_HORIZONTAL,
  },
  {
    label: '纵向联邦-NN模型',
    value: EnumAlgorithmProjectType.NN_VERTICAL,
  },
  // {
  //   label: i18n.t('algorithm_management.label_model_type_tree_vertical'),
  //   value: EnumAlgorithmProjectType.TREE_VERTICAL,
  // },
  // {
  //   label: i18n.t('algorithm_management.label_model_type_tree_horizontal'),
  //   value: EnumAlgorithmProjectType.TREE_HORIZONTAL,
  // },
];

export const AlgorithmSourceText = {
  [EnumAlgorithmProjectSource.USER]: '我方',
  [EnumAlgorithmProjectSource.PRESET]: '系统预置',
  [EnumAlgorithmProjectSource.THIRD_PARTY]: '第三方',
};

export const Avatar: React.FC = () => {
  return <div className={styled.avatar_container} />;
};

export function deleteConfirm(
  algorithm: AlgorithmProject | Algorithm,
  isProject = false,
): Promise<void> {
  return new Promise((resolve, reject) => {
    Modal.confirm({
      className: 'custom-modal',
      style: { width: 360 },
      title: isProject
        ? `确认删除「${algorithm.name}}」?`
        : `确认删除版本「V${(algorithm as Algorithm).version}」?`,
      content: isProject
        ? '删除后，使用该算法的模型训练将无法发起新任务，请谨慎操作'
        : '删除后，使用该算法版本的模型训练将无法发起新任务，请谨慎操作',
      cancelText: '取消',
      okText: '确认',
      okButtonProps: {
        status: 'danger',
      },
      async onConfirm() {
        try {
          await (isProject ? deleteAlgorithmProject(algorithm.id) : deleteAlgorithm(algorithm.id));
          resolve();
        } catch (e) {
          reject(e);
        }
      },
    });
  });
}

export function unpublishConfirm(projectId: ID, algorithm: Algorithm): Promise<void> {
  return new Promise((resolve, reject) => {
    Modal.confirm({
      className: 'custom-modal',
      style: { width: 360 },
      title: `确认撤销发布 「V${algorithm.version}」？`,
      content: '撤销发布后，合作伙伴使用该算法版本的模型训练将无法发起新任务，请谨慎操作',
      cancelText: '取消',
      okText: '确认',
      okButtonProps: {
        status: 'danger',
      },
      async onConfirm() {
        try {
          await unpublishAlgorithm(projectId, algorithm.id);
          resolve();
        } catch (e) {
          reject(e);
        }
      },
    });
  });
}

export function pageSplit(data: any[], page: number, pageSize: number): any[] {
  if (data.length === 0) return [];
  const offset = (page - 1) * pageSize;
  return offset + pageSize >= data.length
    ? data.slice(offset, data.length)
    : data.slice(offset, offset + pageSize);
}

export const FILTER_ALGORITHM_MY_OPERATOR_MAPPER = {
  release_status: FilterOp.IN,
  type: FilterOp.IN,
  name: FilterOp.CONTAIN,
};

export const algorithmReleaseStatusFilters: TableFilterConfig = {
  filters: [
    {
      text: '已发布',
      value: AlgorithmReleaseStatus.RELEASED,
    },
    {
      text: '未发布',
      value: AlgorithmReleaseStatus.UNRELEASED,
    },
  ],
  onFilter: (value: string, record: AlgorithmProject) => {
    return value === record.release_status;
  },
};

export const algorithmTypeFilters: TableFilterConfig = {
  filters: [
    {
      text: '横向联邦-NN模型',
      value: EnumAlgorithmProjectType.NN_HORIZONTAL,
    },
    {
      text: '纵向联邦-NN模型',
      value: EnumAlgorithmProjectType.NN_VERTICAL,
    },
  ],
  onFilter: (value: string, record: AlgorithmProject) => {
    return value === record.type;
  },
};
