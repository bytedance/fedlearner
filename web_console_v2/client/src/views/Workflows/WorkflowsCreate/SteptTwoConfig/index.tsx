import React, { FC, useRef, useState } from 'react'
import styled from 'styled-components'
import { ReactFlowProvider, useStoreState } from 'react-flow-renderer'
import { useToggle } from 'react-use'
import JobFormDrawer, { JobFormDrawerExposedRef } from './JobFormDrawer'
import WorkflowJobsFlowChart, { updateNodeStatusById } from 'components/WorlflowJobsFlowChart'
import { JobNode, JobNodeData, JobNodeStatus } from 'components/WorlflowJobsFlowChart/helpers'
import GridRow from 'components/_base/GridRow'
import { Button, message, Modal, notification } from 'antd'
import { ExclamationCircleOutlined } from '@ant-design/icons'
import { useHistory } from 'react-router-dom'
import { useRecoilValue } from 'recoil'
import { workflowJobsConfigForm, workflowGetters, workflowBasicForm } from 'stores/workflow'
import { useTranslation } from 'react-i18next'
import i18n from 'i18n'
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary'
import { createWorkflow } from 'services/workflow'
import { to } from 'shared/helpers'

const Header = styled.header`
  padding: 13px 20px;
  font-size: 14px;
  line-height: 22px;
  background-color: white;
`
const Footer = styled.footer`
  position: sticky;
  bottom: 0;
  z-index: 1000;
  padding: 15px 36px;
  background-color: white;
`
const ChartTitle = styled.h3`
  margin-bottom: 0;
`

const CanvasAndForm: FC = () => {
  const drawerRef = useRef<JobFormDrawerExposedRef>()
  const jobNodes = useStoreState((store) => store.nodes as JobNode[])
  const history = useHistory()
  const [creating, setCreating] = useToggle(false)
  const { t } = useTranslation()
  const [drawerVisible, toggleDrawerVisible] = useToggle(false)
  const [data, setData] = useState<JobNodeData>()
  const { currentWorkflowTpl } = useRecoilValue(workflowGetters)
  const jobsConfigPayload = useRecoilValue(workflowJobsConfigForm)
  const basicPayload = useRecoilValue(workflowBasicForm)

  return (
    <ErrorBoundary>
      <section>
        <Header>
          <ChartTitle>{t('workflow.our_config')}</ChartTitle>
        </Header>

        <WorkflowJobsFlowChart
          jobs={currentWorkflowTpl.config.job_definitions}
          onJobClick={selectJob}
          onCanvasClick={onCanvasClick}
        />

        <JobFormDrawer
          ref={drawerRef as any}
          data={data}
          visible={drawerVisible}
          toggleVisible={toggleDrawerVisible}
          onConfirm={selectJob}
        />

        <Footer>
          <GridRow gap="12">
            <Button type="primary" loading={creating} onClick={submitToCreate}>
              {t('workflow.btn_send_2_ptcpt')}
            </Button>
            <Button onClick={onPrevStepClick}> {t('previous_step')}</Button>
            <Button onClick={onCancelCreationClick}>{t('cancel')}</Button>
          </GridRow>
        </Footer>
      </section>
    </ErrorBoundary>
  )

  function checkIfAllJobConfigCompleted() {
    const isAllCompleted = jobNodes.every((node) => {
      return node.data.status === JobNodeStatus.Completed
    })

    return isAllCompleted
  }
  // ---------- Handlers ----------------
  function onCanvasClick() {
    drawerRef.current?.validateCurrentJobForm()
    toggleDrawerVisible(false)
  }
  async function selectJob(jobNode: JobNode) {
    updateNodeStatusById({ id: jobNode.id, status: JobNodeStatus.Configuring })

    if (jobNode.data.status !== JobNodeStatus.Configuring) {
      await drawerRef.current?.validateCurrentJobForm()
    }
    if (data) {
      drawerRef.current?.saveCurrentValues()
    }
    setData(jobNode.data)

    toggleDrawerVisible(true)
  }
  async function submitToCreate() {
    if (!checkIfAllJobConfigCompleted()) {
      return message.warn(i18n.t('workflow.msg_config_unfinished'))
    }

    const payload = { config: jobsConfigPayload, ...basicPayload }
    setCreating(true)
    // TODO: Loading splash
    await to(createWorkflow(payload))
    setCreating(false)
  }
  function onPrevStepClick() {
    history.goBack()
  }
  function onCancelCreationClick() {
    Modal.confirm({
      title: i18n.t('workflow.msg_sure_2_cancel_create'),
      icon: <ExclamationCircleOutlined />,
      content: i18n.t('workflow.msg_effect_of_cancel_create'),
      style: {
        top: '30%',
      },
      onOk() {
        history.push('/workflows')
      },
    })
  }
}

const WorkflowsCreateStepTwo: FC = () => {
  return (
    <ReactFlowProvider>
      <CanvasAndForm />
    </ReactFlowProvider>
  )
}

export default WorkflowsCreateStepTwo
