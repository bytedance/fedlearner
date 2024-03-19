import React, { FC, useEffect } from 'react';

import { Modal, Form, Input, Button } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import ButtonWithPopconfirm from 'components/ButtonWithPopconfirm';

import { validNamePattern, MAX_COMMENT_LENGTH } from 'shared/validator';

import styles from './index.module.less';

export interface Props<T = any> {
  visible: boolean;
  isEdit?: boolean;
  isLoading?: boolean;
  initialValues?: any;
  onOk?: (values: T) => void;
  onCancel?: () => void;
}

export interface ModelFormData {
  id?: number;
  name: string;
  comment: string;
}

const ModelFormModal: FC<Props<ModelFormData>> = ({
  visible,
  isEdit = false,
  isLoading = false,
  onOk,
  onCancel,
  initialValues,
}) => {
  const [formInstance] = Form.useForm<any>();

  useEffect(() => {
    if (visible && isEdit && initialValues && formInstance) {
      formInstance.setFieldsValue({
        ...initialValues,
      });
    }
  }, [visible, isEdit, initialValues, formInstance]);

  return (
    <Modal
      title={'编辑模型'}
      visible={visible}
      maskClosable={false}
      afterClose={afterClose}
      onCancel={onCancel}
      footer={null}
    >
      <Form layout="vertical" form={formInstance} onSubmit={onOk}>
        <Form.Item
          field="name"
          label={'模型名称'}
          rules={[
            { required: true, message: '模型集名称为必填项' },
            {
              match: validNamePattern,
              message: '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
            },
          ]}
        >
          <Input disabled={true} />
        </Form.Item>
        <Form.Item
          field="comment"
          label={'模型描述'}
          rules={[{ max: MAX_COMMENT_LENGTH, message: '最多为 200 个字符' }]}
        >
          <Input.TextArea rows={4} placeholder={'最多为 200 个字符'} />
        </Form.Item>
        <Form.Item field="id" style={{ display: 'none' }}>
          <Input />
        </Form.Item>
        <Form.Item wrapperCol={{ span: 24 }} style={{ marginBottom: 0 }}>
          <GridRow className={styles.footer_row} justify="end" gap="12">
            <ButtonWithPopconfirm buttonText={'取消'} onConfirm={onCancel} />
            <Button type="primary" htmlType="submit" loading={isLoading}>
              {isEdit ? '保存' : '创建'}
            </Button>
          </GridRow>
        </Form.Item>
      </Form>
    </Modal>
  );

  function afterClose() {
    // clear all fields
    formInstance.resetFields();
  }
};

export default ModelFormModal;
