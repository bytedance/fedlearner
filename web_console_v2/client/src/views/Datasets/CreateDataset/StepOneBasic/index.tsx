import React, { FC } from 'react';
import styled from 'styled-components';
import { Form, Input, Radio, message, Button, Popconfirm } from 'antd';
import { useTranslation } from 'react-i18next';
import { DatasetCreatePayload, DatasetType } from 'typings/dataset';
import GridRow from 'components/_base/GridRow';
import { useToggle } from 'react-use';
import { useRecoilState, useSetRecoilState } from 'recoil';
import { datasetBasicForm } from 'stores/dataset';

const FooterRow = styled(GridRow)`
  padding-top: 15px;
  border-top: 1px solid var(--backgroundGray);
`;

type Props = {
  onCancel: any;
  onSuccess: any;
};

const StepOneBasic: FC<Props> = ({ onSuccess, onCancel }) => {
  const { t } = useTranslation();
  const [formInstance] = Form.useForm<DatasetCreatePayload>();

  const [formValues, saveToRecoil] = useRecoilState(datasetBasicForm);

  return (
    <Form
      initialValues={{ ...formValues }}
      labelCol={{ span: 6 }}
      wrapperCol={{ span: 18 }}
      style={{ width: '500px' }}
      form={formInstance}
      onFinish={submit}
    >
      <Form.Item
        name="name"
        label={t('dataset.label_name')}
        rules={[{ required: true, message: t('dataset.msg_name_required') }]}
      >
        <Input placeholder={t('dataset.placeholder_name')} />
      </Form.Item>

      <Form.Item
        name="dataset_type"
        label={t('dataset.label_type')}
        rules={[{ required: true, message: t('dataset.msg_type_required') }]}
      >
        <Radio.Group>
          <Radio.Button value={DatasetType.PSI}>PSI</Radio.Button>
          <Radio.Button value={DatasetType.STREAMING}>Streaming</Radio.Button>
        </Radio.Group>
      </Form.Item>

      <Form.Item name="comment" label={t('dataset.label_comment')}>
        <Input.TextArea rows={4} placeholder={t('dataset.placeholder_comment')} />
      </Form.Item>

      <Form.Item wrapperCol={{ span: 24 }} style={{ marginBottom: 0 }}>
        <FooterRow justify="end" gap="12">
          <Popconfirm
            title={t('dataset.msg_quit_warning')}
            cancelText={t('cancel')}
            okText={t('submit')}
            onConfirm={onCancel}
          >
            <Button>{t('cancel')}</Button>
          </Popconfirm>

          <Button type="primary" htmlType="submit">
            {t('next_step')}
          </Button>
        </FooterRow>
      </Form.Item>
    </Form>
  );

  async function submit(value: DatasetCreatePayload) {
    try {
      saveToRecoil({ ...value });
      onSuccess();
    } catch (error) {
      message.error(error.message);
    }
  }
};

export default StepOneBasic;
