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
import { workflowConfigValue } from 'stores/workflow'
import { useTranslation } from 'react-i18next'
import i18n from 'i18n'

const Container = styled.section``
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
  const { t } = useTranslation()
  const [drawerVisible, toggleDrawerVisible] = useToggle(false)
  const [data, setData] = useState<JobNodeData>()
  const configValue = useRecoilValue(workflowConfigValue)

  return (
    <>
      <Container>
        <Header>
          <ChartTitle className="">{t('workflow.our_config')}</ChartTitle>
        </Header>

        <WorkflowJobsFlowChart onJobClick={selectJob} onCanvasClick={onCanvasClick} />

        <JobFormDrawer
          ref={drawerRef as any}
          data={data}
          visible={drawerVisible}
          toggleVisible={toggleDrawerVisible}
          onConfirm={selectJob}
        />

        <Footer>
          <GridRow gap="12">
            <Button type="primary" onClick={onSubmit}>
              {t('workflow.btn_send_2_ptcpt')}
            </Button>
            <Button onClick={onPrevStepClick}> {t('previous_step')}</Button>
            <Button onClick={onCancelCreationClick}>{t('cancel')}</Button>
          </GridRow>
        </Footer>
      </Container>
    </>
  )

  function checkIfAllJobConfigCompleted() {
    return jobNodes.every((node) => {
      return node.data.status === JobNodeStatus.Completed
    })
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
  function onSubmit() {
    if (!checkIfAllJobConfigCompleted()) {
      return message.warn(i18n.t('workflow.msg_config_unfinished'))
    }

    notification.open({
      message: i18n.t('workflow.current_config'),
      description: JSON.stringify(configValue.jobs),
      duration: null,
    })
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
      onCancel() {
        console.log('Cancel')
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
