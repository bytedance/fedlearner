import React, { ReactElement, useState } from 'react'
import styled from 'styled-components'
import CardDescribe from './CardDescribe'
import ProjectAction from '../ProjectAction'
import CreateTime from '../CreateTime'
import ConnectStatus from '../ConnectStatus'
import Detail from '../Detail'
import BaseForm from '../BaseForm'
import { Tooltip, Modal, Form } from 'antd'
import { useTranslation } from 'react-i18next'
import { ReactComponent as CheckConnectIcon } from 'assets/images/check-connect.svg'
import createWorkFlow from 'assets/images/create-work-flow.svg'
import ProjectName from '../ProjectName'

const CardContainer = styled.div`
  height: 208px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e5e6eb;
  box-shadow: 0px 4px 10px #f2f3f5;
`
const CardHeaderContainer = styled.div`
  display: flex;
  height: 40px;
  border-bottom: 1px solid var(--gray3);
  justify-content: space-between;
  .project {
    &-time {
      min-width: 146px;
    }
  }
`

const CardMainContainer = styled.div`
  display: flex;
  padding: 25px 0;
  .project {
    &-work-flow-number {
      font-family: Clarity Mono;
      font-size: 32px;
      line-height: 22px;
      color: var(--textColor);
      margin-top: 12px;
    }
    &-connect-status-wrapper {
      margin-top: 12px;
    }
  }
`

const CardFooterContainer = styled.div`
  flex: 1;
  display: flex;
  padding: 10px;
  .right {
    flex: 1;
    font-size: 12px;
    line-height: 22px;
    color: var(--gray7);
    padding-left: 6px;
  }
  .left {
    display: flex;
    min-width: 80px;
    justify-content: space-between;
  }
`

const CheckConnectStyle = styled.div`
  height: 24px;
  width: 24px;
  padding: 2px 6px 0;
  border-radius: 12px;
  path {
    stroke: #4e4f69;
  }
  &:hover {
    background-color: var(--gray1);
    path {
      stroke: var(--primaryColor);
    }
  }
`

interface CardProps {
  item: Project
}

interface CardHeaderProps {
  name: string
  time: number
}

interface CardMainProps {
  workFlowNumber: number
  connectStatus: number
}

interface CardFooterProps {}

function CardHeader({ name, time }: CardHeaderProps): ReactElement {
  return (
    <CardHeaderContainer>
      {/* FIXME */}
      <ProjectName text={'sadf单dfadfaddfafakashfhjksafk 化开发和f'} />
      <div className="project-time">
        <CreateTime time={time} />
      </div>
    </CardHeaderContainer>
  )
}

function CardMain({ workFlowNumber }: CardMainProps): ReactElement {
  //FIXME
  const random: number = Math.random() * 3.99
  const connectStatus = Math.floor(random)
  const { t } = useTranslation()
  return (
    <CardMainContainer>
      <CardDescribe describe={t('project_workflow_number')}>
        <div className="project-work-flow-number">{workFlowNumber}</div>
      </CardDescribe>
      <CardDescribe describe={t('project_connect_status')}>
        <div className="project-connect-status-wrapper">
          <ConnectStatus connectStatus={connectStatus} />
        </div>
      </CardDescribe>
    </CardMainContainer>
  )
}

function CreateWorkFlow(): ReactElement {
  const { t } = useTranslation()
  return (
    <Tooltip title={t('project_create_work_flow')} placement="top">
      <img src={createWorkFlow} alt="" />
    </Tooltip>
  )
}

function CheckConnect(): ReactElement {
  const { t } = useTranslation()
  return (
    <Tooltip title={t('project_check_connect')} placement="top">
      <CheckConnectStyle>
        <CheckConnectIcon />
      </CheckConnectStyle>
    </Tooltip>
  )
}

function CardFooter({}: CardFooterProps): ReactElement {
  const { t } = useTranslation()
  const creator = '陈胜明'
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [isDrawerVisible, setIsDrawerVisible] = useState(false)
  const [form] = Form.useForm()
  return (
    <CardFooterContainer>
      <div className="right">{creator}</div>
      <div className="left">
        <CheckConnect />
        <CreateWorkFlow />
        <ProjectAction
          onEdit={() => {
            setIsModalVisible(true)
          }}
          onDetail={() => setIsDrawerVisible(true)}
        />
      </div>
      <Modal
        title={t('project_edit')}
        visible={isModalVisible}
        // onOk={}
        onCancel={() => setIsModalVisible(false)}
        width={450}
        zIndex={2000}
        okText={t('submit')}
        cancelText={t('cancel')}
        bodyStyle={{ padding: '24px 0' }}
      >
        <BaseForm form={form} />
      </Modal>
      <Detail title="isaflj" onClose={() => setIsDrawerVisible(false)} visible={isDrawerVisible} />
    </CardFooterContainer>
  )
}

function Card({ item }: CardProps): ReactElement {
  return (
    <CardContainer>
      <CardHeader name={item.name} time={item.time} />
      <CardMain workFlowNumber={2} connectStatus={1} />
      <CardFooter />
    </CardContainer>
  )
}

export default Card
