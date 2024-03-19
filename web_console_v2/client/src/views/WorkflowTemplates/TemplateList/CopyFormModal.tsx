import React, { FC, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Modal, Form, Input, Button, Message } from '@arco-design/web-react';
import {
  createTemplateRevision,
  createWorkflowTemplate,
  fetchTemplateById,
} from 'services/workflow';
import ButtonWithPopconfirm from 'components/ButtonWithPopconfirm';
import { WorkflowTemplate } from 'typings/workflow';
import { validNamePattern } from 'shared/validator';
import { to } from 'shared/helpers';

export interface Props {
  visible: boolean;
  initialValues?: any;
  selectedWorkflowTemplate?: WorkflowTemplate;
  onSuccess?: () => void;
  onFail?: () => void;
  onCancel?: () => void;
}

const CopyFormModal: FC<Props> = ({
  selectedWorkflowTemplate,
  visible,
  onSuccess,
  onFail,
  onCancel,
  initialValues,
}) => {
  const { t } = useTranslation();

  const [isLoading, setIsLoading] = useState(false);

  const [formInstance] = Form.useForm<any>();

  useEffect(() => {
    if (visible && initialValues && formInstance) {
      formInstance.setFieldsValue({
        ...initialValues,
      });
    }
  }, [visible, initialValues, formInstance]);

  return (
    <Modal
      title={t('workflow.title_copy_template')}
      visible={visible}
      maskClosable={false}
      maskStyle={{ backdropFilter: 'blur(4px)' }}
      afterClose={afterClose}
      onCancel={onCancel}
      onOk={onSubmit}
      footer={[
        <ButtonWithPopconfirm buttonText={t('cancel')} onConfirm={onCancel} />,
        <Button type="primary" htmlType="submit" loading={isLoading} onClick={onSubmit}>
          {t('confirm')}
        </Button>,
      ]}
    >
      <Form
        labelCol={{ span: 6 }}
        wrapperCol={{ span: 16 }}
        style={{ width: '500px' }}
        colon={true}
        form={formInstance}
      >
        <Form.Item
          field="name"
          label={t('workflow.title_template_name')}
          rules={[
            { required: true },
            { match: validNamePattern, message: t('valid_error.name_invalid') },
          ]}
        >
          <Input />
        </Form.Item>
      </Form>
    </Modal>
  );

  async function onSubmit() {
    const templateName = formInstance.getFieldValue('name');
    if (!selectedWorkflowTemplate) {
      return;
    }

    const { id } = selectedWorkflowTemplate!;
    setIsLoading(true);
    const [res, err] = await to(fetchTemplateById(id));

    if (err) {
      setIsLoading(false);
      onFail?.();
      return Message.error(t('workflow.msg_get_tpl_detail_failed'));
    }

    const newTplPayload: WorkflowTemplate = res.data;
    newTplPayload.name = templateName;
    newTplPayload.kind = 0;
    const [resp, error] = await to(createWorkflowTemplate(newTplPayload));

    if (error) {
      setIsLoading(false);
      onFail?.();
      return Message.error(error.message);
    }

    await to(createTemplateRevision(resp.data.id));

    Message.success(t('app.copy_success'));
    setIsLoading(false);
    onSuccess?.();
  }

  function afterClose() {
    // Clear all fields
    formInstance.resetFields();
  }
};

export default CopyFormModal;
