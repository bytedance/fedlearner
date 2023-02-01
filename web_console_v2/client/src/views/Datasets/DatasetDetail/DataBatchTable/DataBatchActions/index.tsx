import React from 'react';
import { DataBatchV2, DatasetKindLabel, DatasetStateFront } from 'typings/dataset';
import { Space } from '@arco-design/web-react';
import MoreActions from 'components/MoreActions';
interface IProp {
  data: DataBatchV2;
  onDelete?: () => void;
  onStop?: () => void;
  onExport?: (batchId: ID) => void;
  onRerun?: (batchId: ID, batchName: string) => void;
  kindLabel: DatasetKindLabel;
}

export default function TaskActions(prop: IProp) {
  const { data, kindLabel, onExport, onRerun } = prop;

  const isProcessedDataset = kindLabel === DatasetKindLabel.PROCESSED;
  const isSuccess = data.state === DatasetStateFront.SUCCEEDED;
  const isFailed = data.state === DatasetStateFront.FAILED;
  return (
    <Space>
      <button
        className="custom-text-button"
        style={{
          marginRight: 10,
        }}
        type="button"
        key="rerun-batch"
        disabled={!isFailed}
        onClick={() => onRerun?.(data.id, data.name)}
      >
        重新运行
      </button>
      {isProcessedDataset && (
        <button
          className="custom-text-button"
          style={{
            marginRight: 10,
          }}
          type="button"
          key="export-batch"
          disabled={!isSuccess}
          onClick={() => onExport?.(data.id)}
        >
          导出
        </button>
      )}
      <MoreActions
        actionList={[
          {
            disabled: true,
            label: '删除',
            danger: true,
            onClick() {},
          },
        ]}
      />
    </Space>
  );
}
