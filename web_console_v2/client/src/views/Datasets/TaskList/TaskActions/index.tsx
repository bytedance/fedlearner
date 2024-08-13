import React from 'react';
import { DatasetJobListItem } from 'typings/dataset';
import { isJobRunning } from 'shared/dataset';
import Modal from 'components/Modal';
import { Button, Message, Space } from '@arco-design/web-react';
import MoreActions from 'components/MoreActions';
import { deleteDatasetJob, stopDatasetJob } from 'services/dataset';
import { ButtonProps } from '@arco-design/web-react/es/Button/interface';

interface IProp {
  data: DatasetJobListItem;
  onDelete?: () => void;
  onStop?: () => void;
  buttonProps?: ButtonProps;
}

export default function TaskActions(prop: IProp) {
  const { data, onDelete, onStop, buttonProps } = prop;

  const handleOnJobStop = (projectId: ID, data: DatasetJobListItem) => {
    stopDatasetJob(projectId, data.id!).then(
      () => {
        onStop && onStop();
      },
      (err) => Message.error(`停止失败: ${err?.message}`),
    );
  };

  const handleOnJobDelete = (projectId: ID, data: DatasetJobListItem) => {
    deleteDatasetJob(projectId, data.id!).then(
      () => {
        onDelete && onDelete();
      },
      (err) => Message.error(`删除失败: ${err?.message}`),
    );
  };
  return (
    <Space>
      <Button
        disabled={!isJobRunning(data)}
        onClick={() => {
          Modal.stop({
            title: `确认要停止「${data.result_dataset_name}」？`,
            content: '停止后，该任务不能再重新运行，请谨慎操作',
            onOk() {
              if (!data.project_id) {
                Message.info('请选择工作区');
                return;
              }
              handleOnJobStop(data.project_id, data);
            },
          });
        }}
        {...buttonProps}
      >
        停止运行
      </Button>
      <MoreActions
        actionList={[
          {
            disabled: isJobRunning(data),
            label: '删除',
            danger: true,
            onClick() {
              Modal.delete({
                title: `确认要删除「${data.result_dataset_name}」？`,
                content: '删除后，该任务及信息将无法恢复，请谨慎操作',
                onOk() {
                  if (!data.project_id) {
                    Message.info('请选择工作区');
                    return;
                  }
                  handleOnJobDelete(data.project_id, data);
                },
              });
            },
          },
        ]}
      />
    </Space>
  );
}
