import React, { ReactElement, useState } from 'react'
import styled from 'styled-components'
import CardDescribe from './CardDescribe'
import ProjectAction from '../ProjectAction'
import CreateTime from '../CreateTime'
import ConnectStatus from '../ConnectStatus'
import Detail from '../Detail'
import BaseForm from '../BaseForm'
import { Tooltip, Modal, Drawer } from 'antd'
import { useTranslation } from 'react-i18next'
import { ReactComponent as CheckConnect } from 'assets/images/check-connect.svg'
import createWorkFlow from 'assets/images/create-work-flow.svg'

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
    &-name {
      color: var(--gray10);
      font-weight: 500;
      font-size: 15px;
      line-height: 40px;
      margin-left: 16px;
    }
    &-time {
      margin-right: 16px;
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

function CardHeader(props: CardHeaderProps): ReactElement {
  return (
    <CardHeaderContainer>
      <div className="project-name">发看过你项目</div>
      <div className="project-time">
        <CreateTime time={props.time} />
      </div>
    </CardHeaderContainer>
  )
}

function CardMain(props: CardMainProps): ReactElement {
  const random: number = Math.random() * 3.99
  const connectStatus = Math.ceil(random)
  const { t } = useTranslation()
  return (
    <CardMainContainer>
      <CardDescribe describe={t('project_workflow_number')}>
        <div className="project-work-flow-number">{props.workFlowNumber}</div>
      </CardDescribe>
      <CardDescribe describe={t('project_connect_status')}>
        <div className="project-connect-status-wrapper">
          <ConnectStatus connectStatus={connectStatus} />
        </div>
      </CardDescribe>
    </CardMainContainer>
  )
}

function CardFooter(props: CardFooterProps): ReactElement {
  const { t } = useTranslation()
  const creator = '陈胜明'
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isDrawerVisible, setIsDrawerVisible] = useState(false);
  return (
    <CardFooterContainer>
      <div className="right">{creator}</div>
      <div className="left">
        <Tooltip title={t('project_check_connect')} placement="top">
          <CheckConnectStyle>
            <CheckConnect className="check-connect-icon" />
          </CheckConnectStyle>
        </Tooltip>
        <Tooltip title={t('project_create_work_flow')} placement="top">
          <img src={createWorkFlow} alt="" />
        </Tooltip>
        <ProjectAction onEdit={()=>{setIsModalVisible(true)}} onDetail={()=>setIsDrawerVisible(true)} />
      </div>
      <Modal
        title={t('project_edit')}
        visible={isModalVisible}
        // onOk={}
        onCancel={()=>setIsModalVisible(false)}
        width={400}
        zIndex={2000}
      >
        <BaseForm />
      </Modal>
      <Drawer
        title="isaflj"
        placement="right"
        closable={true}
        onClose={()=>setIsDrawerVisible(false)}
        visible={isDrawerVisible}
        width={880}
      >
        <Detail />
      </Drawer>
    </CardFooterContainer>
  )
}

function Card(props: CardProps): ReactElement {
  return (
    <CardContainer>
      <CardHeader name={props.item.name} time={props.item.time} />
      <CardMain workFlowNumber={2} connectStatus={1} />
      <CardFooter />
    </CardContainer>
  )
}

export default Card
