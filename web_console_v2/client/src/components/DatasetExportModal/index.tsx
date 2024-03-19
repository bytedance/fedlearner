import React, { FC, useState } from 'react';
import { to } from 'shared/helpers';
import { exportDataset } from 'services/dataset';
import { Modal, Form, Input, Button, Message } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import ButtonWithPopconfirm from 'components/ButtonWithPopconfirm';
import { ExportDataset } from 'typings/dataset';
import { removeFalsy } from 'shared/object';
import styled from './index.module.less';
export interface Props {
  visible: boolean;
  id?: ID;
  batchId?: ID;
  onSuccess?: (datasetId: ID, datasetJobId: ID) => void;
  onFail?: () => void;
  onCancel?: () => void;
}

interface FormData {
  export_path: string;
}

const ExportModal: FC<Props> = ({ id, batchId, visible, onSuccess, onFail, onCancel }) => {
  const [isLoading, setIsLoading] = useState(false);

  const [formInstance] = Form.useForm<any>();

  return (
    <Modal
      title="导出数据集"
      visible={visible}
      maskClosable={false}
      afterClose={afterClose}
      onCancel={onCancel}
      footer={null}
    >
      <Form layout="vertical" form={formInstance} onSubmit={onSubmit}>
        <Form.Item field="export_path" label="导出路径" rules={[{ required: true }]}>
          <Input />
        </Form.Item>

        <Form.Item wrapperCol={{ span: 23 }} style={{ marginBottom: 0 }}>
          <GridRow className={styled.footer_grid_row} justify="end" gap="12">
            <ButtonWithPopconfirm buttonText="取消" onConfirm={onCancel} />
            <Button type="primary" htmlType="submit" loading={isLoading}>
              确认
            </Button>
          </GridRow>
        </Form.Item>
      </Form>
    </Modal>
  );

  async function onSubmit(values: FormData) {
    setIsLoading(true);
    const [data, err] = await to(
      exportDataset(
        id!,
        removeFalsy({
          batch_id: batchId,
          export_path: values.export_path,
        }),
      ),
    );
    if (err) {
      setIsLoading(false);
      onFail?.();
      Message.error(err.message || '导出失败');
      return;
    }

    Message.success('导出成功');
    setIsLoading(false);
    const { dataset_job_id, export_dataset_id } = data?.data || ({} as ExportDataset);
    onSuccess?.(export_dataset_id, dataset_job_id);
  }

  function afterClose() {
    // Clear all fields
    formInstance.resetFields();
  }
};

export default ExportModal;
