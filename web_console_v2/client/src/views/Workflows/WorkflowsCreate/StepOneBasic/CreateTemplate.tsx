import React, { FunctionComponent, useCallback } from 'react'
import { Form, Input, message } from 'antd'
import FileUpload from 'components/FileUpload'
import { useTranslation } from 'react-i18next'
import { useRecoilState } from 'recoil'
import { workflowTemplateCreating, StepOneTemplateForm } from 'stores/workflow'
import WORKFLOW_CHANNELS, { workflowPubsub } from '../pubsub'
import { createWorkflowTemplate } from 'services/workflow'
import { useSubscribe } from 'hooks'
import { to } from 'shared/helpers'
import { readJSONFromInput } from 'shared/file'

const CreateTemplateForm: FunctionComponent = () => {
  const { t } = useTranslation()
  const [formInstance] = Form.useForm<StepOneTemplateForm>()
  const [formData, setFormData] = useRecoilState(workflowTemplateCreating)

  const createNewTpl = useCallback(async () => {
    const [payload, validError] = await to(formInstance.validateFields())

    if (validError) {
      return
    }

    const [res, error] = await to(createWorkflowTemplate(payload))

    if (error) {
      return message.error(error.message)
    }

    workflowPubsub.publish(WORKFLOW_CHANNELS.tpl_create_succeed, res.data)
  }, [formInstance])

  // Subscribe if need request to create new one
  useSubscribe(WORKFLOW_CHANNELS.create_new_tpl, createNewTpl)

  return (
    <Form
      initialValues={{ ...formData, _files: [] }}
      labelCol={{ span: 6 }}
      wrapperCol={{ span: 18 }}
      form={formInstance}
      onValuesChange={onFormChange}
    >
      <Form.Item
        name="name"
        label={t('workflow.label_new_template_name')}
        rules={[{ required: true }]}
      >
        <Input placeholder={t('workflow.placeholder_template_name')} />
      </Form.Item>

      <Form.Item name="_files" noStyle>
        <Form.Item
          name="template"
          label={t('workflow.label_upload_template')}
          rules={[{ required: true }]}
        >
          <FileUpload
            showUploadList={false}
            value={formData.template}
            accept=".json"
            maxSize="20MB"
            beforeUpload={beforeUpload}
            onRemoveFile={removeTemplate}
          />
        </Form.Item>
      </Form.Item>

      <Form.Item name="comment" label={t('workflow.label_template_comment')}>
        <Input.TextArea rows={4} placeholder={t('workflow.placeholder_comment')} />
      </Form.Item>
    </Form>
  )

  function onFormChange(_: any, values: StepOneTemplateForm) {
    setFormData(values)
  }

  function beforeUpload(file: File) {
    if (formData.template) {
      message.error(t('workflow.msg_only_1_tpl'))
      return false
    }

    to(readJSONFromInput(file)).then(([tplConfig, error]) => {
      if (error) {
        message.error(error.message)
        return false
      }

      setFormData({
        ...formData,
        template: tplConfig,
      })

      formInstance.setFieldsValue({
        _files: [],
        template: tplConfig,
      })
    })

    return false
  }

  function removeTemplate(eve: any) {
    setFormData({
      ...formData,
      template: '',
    })
    formInstance.setFieldsValue({
      _files: [],
      template: '',
    })
  }
}

export default CreateTemplateForm
