import React, { FC, useState } from 'react'
import styled from 'styled-components'
import { Card, Form, Select, Radio, Button, Input, message } from 'antd'
import { useTranslation } from 'react-i18next'
import GridRow from 'components/_base/GridRow'
import CreateTemplateForm from './CreateTemplate'
import { useHistory } from 'react-router-dom'
import { cloneDeep } from 'lodash'
import {
  currentWorkflowTemplate,
  StepOneForm,
  workflowBasicForm,
  workflowGetters,
  workflowJobsConfigForm,
} from 'stores/workflow'
import { useRecoilState, useRecoilValue, useSetRecoilState } from 'recoil'
import WORKFLOW_CHANNELS, { workflowPubsub } from '../pubsub'
import { useRecoilQuery } from 'hooks/recoil'
import { WorkflowTemplate } from 'typings/workflow'
import { useToggle } from 'react-use'
import { projectListQuery } from 'stores/projects'
import { useQuery } from 'react-query'
import { fetchWorkflowTemplateList } from 'services/workflow'
import { WorkflowCreateProps } from '..'

const FormsContainer = styled.div`
  width: 500px;
  margin: 0 auto;
`

const WorkflowsCreateStepOne: FC<WorkflowCreateProps> = ({ isInitiate, isAccept }) => {
  const { t } = useTranslation()
  const [formInstance] = Form.useForm<StepOneForm>()
  const history = useHistory()
  const [submitting, setSubmitting] = useToggle(false)
  const [is_left, setIsLeft] = useState(isInitiate)
  const [group_alias, setGroupAlias] = useState('')
  const [formData, setFormData] = useRecoilState(workflowBasicForm)
  const setJobsConfigData = useSetRecoilState(workflowJobsConfigForm)
  const { whetherCreateNewTpl } = useRecoilValue(workflowGetters)
  const setWorkflowTemplate = useSetRecoilState(currentWorkflowTemplate)

  const { data: projectList } = useRecoilQuery(projectListQuery)

  const { isLoading: tplLoading, data: tplListRes, error: tplListErr } = useQuery(
    ['fetchWorkflowTemplateList', is_left, group_alias],
    () => fetchWorkflowTemplateList({ is_left, group_alias }),
  )

  const tplList = tplListRes?.data.data || []
  const noAvailableTpl = tplList.length === 0

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
            label={t('workflow.label_name')}
            rules={[{ required: true, message: t('workflow.msg_name_required') }]}
          >
            <Input placeholder={t('workflow.placeholder_name')} />
          </Form.Item>

          <Form.Item
            name="project_id"
            label={t('workflow.label_project')}
            hasFeedback
            rules={[{ required: true, message: t('workflow.msg_project_required') }]}
          >
            <Select placeholder={t('workflow.placeholder_project')}>
              {projectList &&
                projectList.map((pj) => (
                  <Select.Option key={pj.id} value={pj.id}>
                    {pj.name}
                  </Select.Option>
                ))}
            </Select>
          </Form.Item>

          <Form.Item name="forkable" label={t('workflow.label_peer_forkable')}>
            <Radio.Group>
              <Radio value={true}>{t('workflow.label_allow')}</Radio>
              <Radio value={false}>{t('workflow.label_not_allow')}</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item name="_templateType" label={t('workflow.label_template')}>
            <Radio.Group>
              <Radio.Button value={'existing'}>{t('workflow.label_exist_template')}</Radio.Button>
              <Radio.Button value={'create'}>{t('workflow.label_new_template')}</Radio.Button>
            </Radio.Group>
          </Form.Item>

          {/* If choose to use an existing template */}
          {formData._templateType === 'existing' && (
            <Form.Item
              name="_templateSelected"
              wrapperCol={{ offset: 6 }}
              hasFeedback
              rules={[{ required: true, message: t('workflow.msg_template_required') }]}
            >
              {noAvailableTpl && !tplLoading ? (
                <div>暂无可用模板，请新建</div>
              ) : (
                <Select
                  loading={tplLoading}
                  disabled={Boolean(tplListErr) || noAvailableTpl}
                  onChange={onTemplateSelectChange}
                  placeholder={t('workflow.placeholder_template')}
                >
                  {tplList &&
                    tplList.map((tpl) => (
                      <Select.Option key={tpl.id} value={tpl.id}>
                        {tpl.name}
                      </Select.Option>
                    ))}
                </Select>
              )}
            </Form.Item>
          )}
        </Form>

        {/* If choose to create a new template */}
        {formData._templateType === 'create' && (
          <CreateTemplateForm onSuccess={onTplCreateSuccess} onError={onTplCreateError} />
        )}

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

  async function goNextStep() {
    history.push('/workflows/initiate/config')
    workflowPubsub.publish(WORKFLOW_CHANNELS.go_config_step)
  }
  function backToList() {
    history.push('/workflows')
  }
  function setCurrentUsingTemplate(tpl: WorkflowTemplate) {
    setWorkflowTemplate(tpl)
    // Set empty jobs config data once choose different template
    setJobsConfigData(tpl.config)
  }
  // --------- Handlers -----------
  function onFormChange(_: any, values: StepOneForm) {
    setFormData(values)
  }
  function onTemplateSelectChange(id: number) {
    const target = tplList?.find((item) => item.id === id)
    if (!target) return
    setCurrentUsingTemplate(cloneDeep(target))
  }

  function onTplCreateSuccess(res: WorkflowTemplate) {
    setSubmitting(false)
    // After click confirm, once tpl create succeed, go next step
    setCurrentUsingTemplate(res)
    goNextStep()
  }
  function onTplCreateError() {
    setSubmitting(false)
  }
  async function onNextStepClick() {
    try {
      // Any form invalidation happens will throw error to stop the try block
      await formInstance.validateFields()

      if (whetherCreateNewTpl) {
        // If the template is newly create, stop the flow and
        // notify the create-template form to send a creation request
        // then waiting for crearte succeed
        // see the subscription of WORKFLOW_CHANNELS.tpl_create_succeed above
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
