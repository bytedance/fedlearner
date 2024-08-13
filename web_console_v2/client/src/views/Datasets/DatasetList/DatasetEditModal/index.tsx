import React, { FC, useEffect } from 'react';
import { to } from 'shared/helpers';
import { MAX_COMMENT_LENGTH, validNamePattern } from 'shared/validator';
import { forceToRefreshQuery } from 'shared/queryClient';
import { editDataset } from 'services/dataset';

import { Modal, Button, Message, Form, Input } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';

import ButtonWithPopconfirm from 'components/ButtonWithPopconfirm';
import { DATASET_LIST_QUERY_KEY } from '../DatasetTable';

import { Dataset, DatasetEditDisplay } from 'typings/dataset';
import styled from './index.module.less';

type Props = {
  dataset: Dataset;
  visible: boolean;
  toggleVisible: (v: boolean) => void;
  onSuccess: Function;
} & React.ComponentProps<typeof Modal>;

const DatasetEditModal: FC<Props> = ({ dataset, visible, toggleVisible, onSuccess, ...props }) => {
  const [form] = Form.useForm<DatasetEditDisplay>();
  const { id, name, comment } = dataset;

  useEffect(() => {
    if (visible && form && dataset) {
      form.setFieldsValue({
        name: dataset.name,
        comment: dataset.comment,
      });
    }
  }, [visible, form, dataset]);

  return (
    <Modal
      title="编辑数据集"
      visible={visible}
      maskClosable={false}
      maskStyle={{ backdropFilter: 'blur(4px)' }}
      afterClose={afterClose}
      onCancel={closeModal}
      footer={null}
      {...props}
    >
      <Form initialValues={{ name, comment }} layout="vertical" form={form} onSubmit={submit}>
        <Form.Item
          label="数据集名称"
          field="name"
          rules={[
            { required: true, message: 'Please input dataset name!' },
            {
              match: validNamePattern,
              message: '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
            },
          ]}
        >
          <Input placeholder="请输入数据集名称" disabled={true} />
        </Form.Item>
        <Form.Item
          label="数据集描述"
          field="comment"
          rules={[{ maxLength: MAX_COMMENT_LENGTH, message: '最多为 200 个字符' }]}
        >
          <Input.TextArea
            placeholder="最多为 200 个字符"
            maxLength={MAX_COMMENT_LENGTH}
            showWordLimit
          />
        </Form.Item>

        <Form.Item wrapperCol={{ span: 24 }} style={{ marginBottom: 0 }}>
          <GridRow className={styled.footer_row} justify="end" gap="12">
            <ButtonWithPopconfirm buttonText="取消" onConfirm={closeModal} />
            <Button type="primary" htmlType="submit">
              保存
            </Button>
          </GridRow>
        </Form.Item>
      </Form>
    </Modal>
  );

  function closeModal() {
    toggleVisible(false);
  }

  async function submit(values: { name: string; comment?: string }) {
    if (!form) {
      return;
    }
    const { comment } = values;
    const [res, error] = await to(editDataset(id, { comment }));
    if (error) {
      Message.error(error.message);
      return;
    }
    Message.success('数据集编辑成功');
    closeModal();
    // Force to refresh the dataset list
    forceToRefreshQuery(DATASET_LIST_QUERY_KEY);
    onSuccess(res);
  }

  function afterClose() {
    // Clear all fields
    form.resetFields();
  }
};

export default DatasetEditModal;
