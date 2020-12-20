import React, { ReactElement, useState } from 'react'
import styled from 'styled-components'
import ProjectAction from '../ProjectAction'
import { ReactComponent as CheckConnectIcon } from 'assets/images/check-connect.svg'
import { ReactComponent as CreateWorkFlow } from 'assets/images/create-work-flow.svg'
import { Modal, Form } from 'antd'
import { useTranslation } from 'react-i18next'
import BaseForm from '../BaseForm'

const Container = styled.div`
  width: 100%;
  display: flex;
`

const Right = styled.div`
  flex: 1;
  display: flex;
`

const Left = styled.div`
  max-width: 440px;
  display: flex;
  align-items: flex-end;
  margin-right: 30px;
  .more {
    font-size: 12px;
    line-height: 28px;
    color: #424e66;
  }
`

const ProjectName = styled.div`
  font-weight: 500;
  font-size: 20px;
  line-height: 28px;
  color: var(--textColor);
`

const Status = styled.div`
  background: #eaf0fe;
  border-radius: 2px;
  padding: 1px 8px;
  height: 24px;
  margin: 2px 8px;
  .text {
    font-weight: 500;
    font-size: 13px;
    line-height: 22px;
    color: var(--primaryColor);
  }
`

const HeaderActionContainer = styled.div`
  background: #f2f3f5;
  border-radius: 2px;
  margin: 0 8px;
  height: 28px;
  padding: 0 10px;
  .aciton-icon {
    margin-top: 2px;
  }
  &:hover {
    background: #e5e6eb;
    circle {
      fill: #e5e6eb;
    }
  }
`

const CheckConnectStyle = styled.div`
  height: 28px;
  display: flex;
  .connect-icon {
    height: 12px;
    width: 12px;
    margin-top: 8px;
    margin-right: 4px;
    path {
      stroke: #424e66;
    }
  }
  .connect-describe {
    font-size: 12px;
    line-height: 28px;
    color: #424e66;
  }
`

const CreateWorkFlowContainer = styled.div`
  height: 28px;
  display: flex;
  circle {
    fill: #f2f3f5;
  }
  .create-describe {
    font-size: 12px;
    line-height: 28px;
    color: #424e66;
  }
  .create-icon {
    margin-top: 2px;
  }
`

const ActionListContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 44px;
  padding: 6px 0;
  border-radius: 4px;
  .actionItem {
    flex: 1;
    width: 100%;
    background-color: transparent;
    line-height: 30px;
    padding-left: 12px;
    &:hover {
      background-color: var(--gray1);
    }
  }
`

interface HeaderActionProps {
  children: React.ReactNode
}

interface ActionListProps {
  onEdit: () => void
}

function CreateWorkFlowAction(): ReactElement {
  const { t } = useTranslation()
  return (
    <CreateWorkFlowContainer>
      <CreateWorkFlow className="create-icon" />
      <div className="create-describe">{t('project_create_work_flow')}</div>
    </CreateWorkFlowContainer>
  )
}

function CheckConnect(): ReactElement {
  const { t } = useTranslation()
  return (
    <CheckConnectStyle>
      <CheckConnectIcon className="connect-icon" />
      <div className="connect-describe">{t('project_check_connect')}</div>
    </CheckConnectStyle>
  )
}

function HeaderAction({ children }: HeaderActionProps): ReactElement {
  return <HeaderActionContainer>{children}</HeaderActionContainer>
}

function ActionList({ onEdit }: ActionListProps): ReactElement {
  const { t } = useTranslation()
  return (
    <ActionListContainer>
      <div className="actionItem" onClick={onEdit}>
        {t('project_action_edit')}
      </div>
    </ActionListContainer>
  )
}

function DetailHeader(): ReactElement {
  const { t } = useTranslation()
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [form] = Form.useForm()
  return (
    <Container>
      <Right>
        {/* FIXME\ */}
        <ProjectName>大发放的f</ProjectName>
        <Status>
          {/* FIXME */}
          <div className="text">连接检查中</div>
        </Status>
      </Right>
      <Left>
        <HeaderAction>
          <CheckConnect />
        </HeaderAction>
        <HeaderAction>
          <CreateWorkFlowAction />
        </HeaderAction>
        <HeaderAction>
          <ProjectAction
            suffix={<div className="more">{t('more')}</div>}
            actionList={
              <ActionList
                onEdit={() => {
                  setIsModalVisible(true)
                }}
              />
            }
          />
        </HeaderAction>
      </Left>
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
    </Container>
  )
}

export default DetailHeader
