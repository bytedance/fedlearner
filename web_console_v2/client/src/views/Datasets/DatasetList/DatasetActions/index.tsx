import React, { FC, useMemo } from 'react';
import { Dataset, DatasetKindLabel } from 'typings/dataset';
import GridRow from 'components/_base/GridRow';
import { ButtonProps, Popconfirm } from '@arco-design/web-react';
import DatasetEditModal from '../DatasetEditModal';
import { useToggle } from 'react-use';
import MoreActions from 'components/MoreActions';
import { isFrontendDeleting, isFrontendProcessing, isFrontendSucceeded } from 'shared/dataset';
import { isDatasetTicket, isDatasetPublished } from 'views/Datasets/shared';
import { isFrontendAuthorized } from 'views/Datasets/shared';
import styled from './index.module.less';

export type DatasetAction =
  | 'delete'
  | 'publish-to-project'
  | 'export'
  | 'authorize'
  | 'cancel-authorize';
type Props = {
  dataset: Dataset;
  type: ButtonProps['type'];
  onPerformAction: (args: { action: DatasetAction; dataset: Dataset }) => void;
  kindLabel: DatasetKindLabel;
};

const DatasetActions: FC<Props> = ({ dataset, type = 'default', onPerformAction, kindLabel }) => {
  const [editModalVisible, toggleEditModalVisible] = useToggle(false);

  const isProcessing = isFrontendProcessing(dataset);
  const isSuccess = isFrontendSucceeded(dataset);
  const isDeleting = isFrontendDeleting(dataset);
  const isAuthorized = isFrontendAuthorized(dataset);
  const isProcessedDataset = kindLabel === DatasetKindLabel.PROCESSED;
  // 表示当前数据集是否处于审批环节
  const isTicket = isDatasetTicket(dataset);
  const isPublished = isDatasetPublished(dataset);
  // 老数据禁用授权及撤销授权功能
  const isDisabledAuth = useMemo(() => {
    const participantsMap = dataset?.participants_info?.participants_map;
    if (!participantsMap) return true;
    return !Boolean(Object.keys(participantsMap).length > 0);
  }, [dataset]);

  const actionList = [
    {
      label: '编辑',
      onClick: onEditClick,
      disabled: isProcessing || isDeleting,
    },
    {
      label: '删除',
      onClick: onDeleteClick,
      danger: true,
      disabled: isProcessing || isDeleting,
    },
  ];

  return (
    <>
      <GridRow {...{ type }}>
        {isProcessedDataset && isAuthorized && (
          <Popconfirm
            title={`确认撤销对 ${dataset.name} 的授权？`}
            disabled={isDisabledAuth}
            onOk={onCancelAuthorizeClick}
          >
            <button
              className={`custom-text-button ${isDisabledAuth ? styled.disabled : ''}`}
              style={{
                marginRight: 10,
              }}
              type="button"
            >
              撤销授权
            </button>
          </Popconfirm>
        )}
        {isProcessedDataset && !isAuthorized && (
          <button
            className="custom-text-button"
            style={{
              marginRight: 10,
            }}
            type="button"
            onClick={onAuthorizeClick}
            disabled={isDisabledAuth}
          >
            授权
          </button>
        )}
        {!isProcessedDataset && !isTicket && (
          <button
            className="custom-text-button"
            style={{
              marginRight: 10,
            }}
            type="button"
            disabled={!isSuccess}
            onClick={onPublishClick}
          >
            {isPublished ? '撤销发布' : '发布'}
          </button>
        )}
        {isProcessedDataset && (
          <button
            className="custom-text-button"
            style={{
              marginRight: 10,
            }}
            type="button"
            key="edit-dataset"
            disabled={!isSuccess} // new processed dataset can't be exported
            onClick={onExportClick}
          >
            导出
          </button>
        )}
        <MoreActions actionList={actionList} />
      </GridRow>
      <DatasetEditModal
        dataset={dataset}
        visible={editModalVisible}
        toggleVisible={toggleEditModalVisible}
        onSuccess={onEditSuccess}
      />
    </>
  );

  function onEditClick() {
    toggleEditModalVisible(true);
  }
  function onDeleteClick() {
    onPerformAction?.({ action: 'delete', dataset });
  }

  function onEditSuccess() {}

  function onPublishClick() {
    onPerformAction?.({ action: 'publish-to-project', dataset });
  }

  function onExportClick() {
    onPerformAction?.({ action: 'export', dataset });
  }

  function onAuthorizeClick() {
    onPerformAction?.({ action: 'authorize', dataset });
  }

  function onCancelAuthorizeClick() {
    onPerformAction?.({ action: 'cancel-authorize', dataset });
  }
};

export default DatasetActions;
