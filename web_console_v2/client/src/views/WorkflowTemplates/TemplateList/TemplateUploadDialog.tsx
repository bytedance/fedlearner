import React, { FC, useCallback } from 'react';
import { Form, Input, message, Modal } from 'antd';
import ReadFile from 'components/ReadFile';
import { useTranslation } from 'react-i18next';
import { CreateTemplateForm } from 'stores/workflow';
import { createWorkflowTemplate } from 'services/workflow';
import { to } from 'shared/helpers';
import { removePrivate } from 'shared/object';
import { readAsJSONFromFile } from 'shared/file';
import { WorkflowTemplatePayload, WorkflowTemplate } from 'typings/workflow';
import { stringifyComplexDictField } from 'shared/formSchema';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import i18n from 'i18n';
import { useToggle } from 'react-use';
import { useHistory } from 'react-router';
import { forceToRefreshQuery } from 'shared/queryClient';
import { TPL_LIST_QUERY_KEY } from '.';

const CreateTemplate: FC = () => {
  const { t } = useTranslation();
  const history = useHistory();
  const [formInstance] = Form.useForm<CreateTemplateForm>();
  const [visible, toggleVisible] = useToggle(true);

  const createNewTpl = useCallback(async () => {
    const [values, validError] = await to(formInstance.validateFields());

    if (validError) {
      return;
    }

    const payload = stringifyComplexDictField(removePrivate(values) as WorkflowTemplatePayload);

    const [, error] = await to(createWorkflowTemplate(payload));

    if (error) {
      return message.error(error.message);
    }

    forceToRefreshQuery(TPL_LIST_QUERY_KEY);

    toggleVisible(false);
  }, [formInstance, toggleVisible]);

  return (
    <Modal
      title={t('workflow.btn_upload_tpl')}
      visible={visible}
      style={{ top: '20%' }}
      maskStyle={{ backdropFilter: 'blur(4px)' }}
      width="600px"
      closable={false}
      maskClosable={false}
      keyboard={false}
      afterClose={afterClose}
      getContainer="body"
      zIndex={Z_INDEX_GREATER_THAN_HEADER}
      onCancel={() => toggleVisible(false)}
      onOk={onSubmit}
    >
      <Form labelCol={{ span: 6 }} wrapperCol={{ span: 16 }} form={formInstance} labelAlign="left">
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
    </Modal>
  );

  async function onSubmit() {
    createNewTpl();
  }

  function afterClose() {
    history.push('/workflow-templates');
  }

  async function readConfig(file: File) {
    try {
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

      return config;
    } catch (error) {
      message.error(error.message);
    }
  }
};

export default CreateTemplate;
