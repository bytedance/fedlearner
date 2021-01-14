import React, { FC, useCallback } from 'react';
import { Form, Input, message } from 'antd';
import ReadFile from 'components/ReadFile';
import { useTranslation } from 'react-i18next';
import { useRecoilState } from 'recoil';
import { workflowTemplateForm, StepOneTemplateForm } from 'stores/workflow';
import WORKFLOW_CHANNELS from '../pubsub';
import { initiateAWorkflowTemplate } from 'services/workflow';
import { useSubscribe } from 'hooks';
import { to } from 'shared/helpers';
import { removePrivate } from 'shared/object';
import { readAsJSONFromFile } from 'shared/file';
import { WorkflowTemplatePayload, WorkflowTemplate } from 'typings/workflow';
import { stringifyWidgetSchemas } from 'shared/formSchema';
import i18n from 'i18n';

type Props = {
  onSuccess?(res: any): void;
  onError?(error: any): void;
  groupAlias?: string;
  isLeft?: boolean;
};

const CreateTemplateForm: FC<Props> = ({ onSuccess, onError, groupAlias, isLeft }) => {
  const { t } = useTranslation();
  const [formInstance] = Form.useForm<StepOneTemplateForm>();
  const [formData, setFormData] = useRecoilState(workflowTemplateForm);

  const createNewTpl = useCallback(async () => {
    const [values, validError] = await to(formInstance.validateFields());

    if (validError) {
      onError && onError(validError);
      return;
    }

    const payload = stringifyWidgetSchemas(removePrivate(values) as WorkflowTemplatePayload);

    const [res, error] = await to(initiateAWorkflowTemplate(payload));

    if (error) {
      onError && onError(error);
      return message.error(error.message);
    }

    onSuccess && onSuccess(res.data.data);
  }, [formInstance, onError, onSuccess]);

  // Subscribe if need request to create new one
  useSubscribe(WORKFLOW_CHANNELS.create_new_tpl, createNewTpl);

  return (
    <Form
      initialValues={{ ...formData }}
      labelCol={{ span: 6 }}
      wrapperCol={{ span: 18 }}
      form={formInstance}
      onValuesChange={onFormChange}
    >
      <Form.Item
        name="name"
        label={t('workflow.label_new_template_name')}
        rules={[{ required: true, message: t('workflow.msg_tpl_name_required') }]}
      >
        <Input placeholder={t('workflow.placeholder_template_name')} />
      </Form.Item>

      <Form.Item
        name="config"
        label={t('workflow.label_upload_template')}
        rules={[{ required: true, message: t('workflow.msg_tpl_file_required') }]}
      >
        <ReadFile accept=".json" reader={readConfig} maxSize={20} />
      </Form.Item>

      <Form.Item name="comment" label={t('workflow.label_template_comment')}>
        <Input.TextArea rows={4} placeholder={t('workflow.placeholder_comment')} />
      </Form.Item>
    </Form>
  );

  function onFormChange(_: any, values: StepOneTemplateForm) {
    setFormData(values);
  }

  async function readConfig(file: File) {
    const template = await readAsJSONFromFile<WorkflowTemplate>(file);
    if (!template.config) {
      message.error(i18n.t('workflow.msg_tpl_config_missing'));
      return;
    }
    const { config } = template;
    if (!config.group_alias) {
      message.error(i18n.t('workflow.msg_tpl_alias_missing'));
      return;
    }
    if (config.is_left === undefined) {
      message.error(i18n.t('workflow.msg_tpl_is_left_missing'));
      return;
    }
    if (isLeft === false && groupAlias) {
      if (config.is_left === true) {
        message.error(i18n.t('workflow.msg_tpl_is_left_wrong'));
        return;
      }
      if (config.group_alias !== groupAlias) {
        message.error(i18n.t('workflow.msg_tpl_alias_wrong'));
        return;
      }
    }
    return config;
  }
};

export default CreateTemplateForm;
