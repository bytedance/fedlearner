import React, { FC, useCallback } from 'react'
import { Form, Input, message } from 'antd'
import FileUpload from 'components/FileUpload'
import { useTranslation } from 'react-i18next'
import { useRecoilState } from 'recoil'
import { workflowTemplateForm, StepOneTemplateForm } from 'stores/workflow'
import WORKFLOW_CHANNELS from '../pubsub'
import { createWorkflowTemplate } from 'services/workflow'
import { useSubscribe } from 'hooks'
import { to } from 'shared/helpers'
import { removePrivate } from 'shared/object'
import { readJSONFromInput } from 'shared/file'
import { WorkflowTemplatePayload } from 'typings/workflow'
import { stringifyWidgetSchemas } from 'shared/formSchema'

type Props = {
  onSuccess?(res: any): void
  onError?(error: any): void
}

const CreateTemplateForm: FC<Props> = ({ onSuccess, onError }) => {
  const { t } = useTranslation()
  const [formInstance] = Form.useForm<StepOneTemplateForm>()
  const [formData, setFormData] = useRecoilState(workflowTemplateForm)

  const createNewTpl = useCallback(async () => {
    const [values, validError] = await to(formInstance.validateFields())

    if (validError) {
      onError && onError(validError)
      return
    }

    const payload = stringifyWidgetSchemas(removePrivate(values) as WorkflowTemplatePayload)

    const [res, error] = await to(createWorkflowTemplate(payload))

    if (error) {
      onError && onError(error)
      return message.error(error.message)
    }

    onSuccess && onSuccess(res.data.data)
  }, [formInstance, onError, onSuccess])

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
          name="config"
          label={t('workflow.label_upload_template')}
          rules={[{ required: true }]}
        >
          <FileUpload
            showUploadList={false}
            value={formData.config}
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
    if (formData.config) {
      message.error(t('workflow.msg_only_1_tpl'))
      return false
    }

    to(readJSONFromInput(file)).then(([tplConfig, error]) => {
      if (error) {
        message.error(error.message)
        return
      }

      setFormData({
        ...formData,
        config: tplConfig,
      })

      formInstance.setFieldsValue({
        _files: [],
        config: tplConfig,
      })
    })

    return false
  }

  function removeTemplate() {
    setFormData({
      ...formData,
      config: '',
    })
    formInstance.setFieldsValue({
      _files: [],
      config: '',
    })
  }
}

export default CreateTemplateForm
