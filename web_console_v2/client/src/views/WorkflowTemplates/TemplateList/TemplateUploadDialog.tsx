import React, { FC, useCallback, useState } from 'react';
import { Message, Button, Input, Modal, Form } from '@arco-design/web-react';
import ReadFile from 'components/ReadFile';
import { CreateTemplateForm } from 'stores/workflow';
import { createWorkflowTemplate } from 'services/workflow';
import { to } from 'shared/helpers';
import { removePrivate } from 'shared/object';
import { readAsJSONFromFile } from 'shared/file';
import {
  WorkflowTemplatePayload,
  WorkflowTemplate,
  WorkflowTemplateEditInfo,
} from 'typings/workflow';
import { stringifyComplexDictField } from 'shared/formSchema';
import { useToggle } from 'react-use';
import { useHistory } from 'react-router';
import { forceToRefreshQuery } from 'shared/queryClient';
import { TPL_LIST_QUERY_KEY } from '.';
import i18n from 'i18n';
import ButtonWithPopconfirm from 'components/ButtonWithPopconfirm';

const CreateTemplate: FC = () => {
  const history = useHistory();
  const [formInstance] = Form.useForm<CreateTemplateForm>();
  const [visible, toggleVisible] = useToggle(true);
  const [editorInfo, setEditorInfo] = useState<WorkflowTemplateEditInfo>();
  const createNewTpl = useCallback(async () => {
    const [values, validError] = await to(formInstance.validate());

    if (validError) {
      return;
    }

    // Get editor_info from uploaded template.
    values.editor_info = editorInfo;

    const payload = stringifyComplexDictField(removePrivate(values) as WorkflowTemplatePayload);

    const [, error] = await to(createWorkflowTemplate(payload));

    if (error) {
      return Message.error(error.message);
    }

    forceToRefreshQuery(TPL_LIST_QUERY_KEY);

    toggleVisible(false);
  }, [formInstance, toggleVisible, editorInfo]);

  return (
    <Modal
      title="上传模板"
      visible={visible}
      style={{ width: '600px' }}
      maskStyle={{ backdropFilter: 'blur(4px)' }}
      closable={true}
      maskClosable={false}
      afterClose={afterClose}
      onCancel={onCancel}
      onOk={onSubmit}
      footer={[
        <ButtonWithPopconfirm key="back" buttonText={i18n.t('cancel')} onConfirm={onCancel} />,
        <Button key="submit" type="primary" onClick={onSubmit}>
          {i18n.t('submit')}
        </Button>,
      ]}
    >
      <Form
        labelCol={{ span: 6 }}
        wrapperCol={{ span: 16 }}
        colon={true}
        form={formInstance}
        labelAlign="left"
      >
        <Form.Item
          field="name"
          label="模板名称"
          rules={[{ required: true, message: '请输入模板名！' }]}
        >
          <Input placeholder="请输入模板名称" />
        </Form.Item>

        <Form.Item
          field="config"
          label="上传模板文件"
          rules={[{ required: true, message: '请选择一个合适的模板文件！' }]}
        >
          <ReadFile accept=".json" reader={readConfig} maxSize={20} />
        </Form.Item>

        <Form.Item field="comment" label="工作流模板描述">
          <Input.TextArea rows={4} placeholder="请输入工作流模板描述" />
        </Form.Item>
      </Form>
    </Modal>
  );

  async function onSubmit() {
    createNewTpl();
  }
  function onCancel() {
    toggleVisible(false);
  }

  function afterClose() {
    history.push(`/workflow-center/workflow-templates`);
  }

  async function readConfig(file: File) {
    try {
      const template = await readAsJSONFromFile<WorkflowTemplate>(file);
      if (!template.config) {
        Message.error('模板格式错误，缺少 config 字段！');
        return;
      }
      const { config, editor_info } = template;
      if (!config.group_alias) {
        Message.error('模板格式错误，缺少 config.group_alias 字段！');
        return;
      }
      setEditorInfo(editor_info);

      return config;
    } catch (error) {
      Message.error(error.message);
    }
  }
};

export default CreateTemplate;
