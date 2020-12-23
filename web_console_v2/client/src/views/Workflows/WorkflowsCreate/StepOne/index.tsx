import React, { useCallback, useEffect } from 'react'
import styled from 'styled-components'
import { Card, Form, Select, Radio, Button, Input, message } from 'antd'
import { useTranslation } from 'react-i18next'
import GridRow from 'components/_base/GridRow'
import CreateTemplateForm from './CreateTemplate'
import { useHistory } from 'react-router-dom'
import {
  currentWorkflowConfig,
  forceReloadTplList,
  StepOneForm,
  workflowCreating,
  workflowGetters,
  workflowTemplateListQuery,
} from 'stores/workflow'
import { useRecoilState, useRecoilValue, useSetRecoilState } from 'recoil'
import WORKFLOW_CHANNELS, { workflowPubsub } from '../pubsub'
import { useSubscribe } from 'hooks'
import { useRecoilQuery } from 'hooks/recoil'
import { WorkflowTemplate } from 'typings/workflow'
import { useToggle } from 'react-use'

const { Option } = Select

const FormsContainer = styled.div`
  width: 500px;
  margin: 0 auto;
`

function WorkflowsCreateStepOne() {
  const { t } = useTranslation()
  const [formInstance] = Form.useForm<StepOneForm>()
  const history = useHistory()
  const [submitting, setSubmitting] = useToggle(false)
  const [formData, setFormData] = useRecoilState(workflowCreating)
  const { whetherCreateNewTpl } = useRecoilValue(workflowGetters)
  const reloadTplList = useSetRecoilState(forceReloadTplList)
  const setWorflowConfig = useSetRecoilState(currentWorkflowConfig)

  const { isLoading: tplLoading, data: tplList, error: tplListErr } = useRecoilQuery(
    workflowTemplateListQuery,
  )

  useEffect(() => {
    if (tplListErr) {
      message.error(tplListErr.message)
    }
  }, [tplListErr])

  useSubscribe(WORKFLOW_CHANNELS.tpl_create_succeed, (_: string, res: WorkflowTemplate) => {
    setWorflowConfig(res.config)
    goNextStep()
  })

  const backToList = useCallback(() => {
    history.push('/workflows')
  }, [history])

  return (
    <Card>
      <FormsContainer>
        <Form
          labelCol={{ span: 6 }}
          wrapperCol={{ span: 18 }}
          form={formInstance}
          onValuesChange={onFormChange as any}
          initialValues={{ ...formData }}
        >
          <Form.Item
            name="name"
            hasFeedback
            label={t('workflows.label_name')}
            rules={[{ required: true }]}
          >
            <Input placeholder={t('workflows.placeholder_name')} />
          </Form.Item>

          <Form.Item
            name="project_token"
            label={t('workflows.label_project')}
            hasFeedback
            rules={[{ required: true, message: 'Please select your country!' }]}
          >
            <Select placeholder={t('workflows.placeholder_project')}>
              <Option value="1">Project - 1</Option>
            </Select>
          </Form.Item>

          <Form.Item name="peer_forkable" label={t('workflows.label_peer_forkable')}>
            <Radio.Group>
              <Radio value={true}>{t('workflows.label_allow')}</Radio>
              <Radio value={false}>{t('workflows.label_not_allow')}</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item name="_templateType" label={t('workflows.label_template')}>
            <Radio.Group>
              <Radio.Button value={'existed'}>{t('workflows.label_exist_template')}</Radio.Button>
              <Radio.Button value={'create'}>{t('workflows.label_new_template')}</Radio.Button>
            </Radio.Group>
          </Form.Item>

          {/* If choose to use an existed template */}
          {formData._templateType === 'existed' && (
            <Form.Item
              name="_templateSelected"
              wrapperCol={{ offset: 6 }}
              hasFeedback
              validateStatus={tplListErr && ('error' as any)}
              help={
                tplListErr && (
                  <>
                    {t('msg_get_template_failed')}
                    <Button size="small" type="link" onClick={() => reloadTplList(Math.random())}>
                      {t('click_to_retry')}
                    </Button>
                  </>
                )
              }
              rules={[{ required: true, message: t('workflows.msg_template_required') }]}
            >
              <Select
                loading={tplLoading}
                disabled={!!tplListErr}
                onChange={onTemplateSelectChange}
                placeholder={t('workflows.placeholder_template')}
              >
                {tplList &&
                  tplList.map((tpl) => (
                    <Option key={tpl.id} value={tpl.id}>
                      {tpl.name}
                    </Option>
                  ))}
              </Select>
            </Form.Item>
          )}
        </Form>

        {/* If choose to create a new template */}
        {formData._templateType === 'create' && <CreateTemplateForm />}

        <Form.Item wrapperCol={{ offset: 6 }}>
          <GridRow gap={16} top="12">
            <Button type="primary" htmlType="submit" loading={submitting} onClick={onNextStepClick}>
              {t('next_step')}
            </Button>

            <Button disabled={submitting} onClick={backToList}>
              {t('cancel')}
            </Button>
          </GridRow>
        </Form.Item>
      </FormsContainer>
    </Card>
  )

  function onFormChange(_: any, values: StepOneForm) {
    setFormData(values)
  }

  function onTemplateSelectChange(id: number) {
    const target = tplList?.find((item) => item.id === id)
    if (!target) return
    setWorflowConfig(target.config)
  }

  async function goNextStep() {
    setSubmitting(false)
    workflowPubsub.publish(WORKFLOW_CHANNELS.go_config_step)
  }

  async function onNextStepClick() {
    try {
      // Any form invalid happens will throw error to stop the try block
      await formInstance.validateFields()

      if (whetherCreateNewTpl) {
        // If the template is newly create, stop the flow and
        // notify the create-template form to send a creation request
        // then waiting for crearte succeed
        setSubmitting(true)
        return workflowPubsub.publish(WORKFLOW_CHANNELS.create_new_tpl)
      } else {
        // And if not
        // just carry on next step
        goNextStep()
      }
    } catch {
      /** ignore validation error */
    }
  }
}

export default WorkflowsCreateStepOne
