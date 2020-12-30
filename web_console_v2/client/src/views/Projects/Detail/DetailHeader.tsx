import React, { ReactElement, useState } from 'react'
import styled from 'styled-components'
import ProjectAction from '../ProjectAction'
import { ReactComponent as CheckConnectionIcon } from 'assets/images/check-connect.svg'
import { ReactComponent as CreateWorkFlow } from 'assets/images/create-work-flow.svg'
import { useTranslation } from 'react-i18next'
import { useHistory } from 'react-router-dom'

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

const CheckConnectionStyle = styled.div`
  height: 28px;
  display: flex;
  cursor: pointer;
  .connection-icon {
    height: 12px;
    width: 12px;
    margin-top: 8px;
    margin-right: 4px;
    path {
      stroke: #424e66;
    }
  }
  .connection-describe {
    font-size: 12px;
    line-height: 28px;
    color: #424e66;
  }
`

const CreateWorkFlowContainer = styled.div`
  height: 28px;
  display: flex;
  cursor: pointer;
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
    cursor: pointer;
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

interface DetailHeaderProps {
  project: Project
}

function CreateWorkFlowAction(): ReactElement {
  const { t } = useTranslation()
  return (
    <CreateWorkFlowContainer>
      <CreateWorkFlow className="create-icon" />
      <div className="create-describe">{t('project.create_work_flow')}</div>
    </CreateWorkFlowContainer>
  )
}

function CheckConnection(): ReactElement {
  const { t } = useTranslation()
  return (
    <CheckConnectionStyle>
      <CheckConnectionIcon className="connection-icon" />
      <div className="connection-describe">{t('project.check_connection')}</div>
    </CheckConnectionStyle>
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
        {t('project.action_edit')}
      </div>
    </ActionListContainer>
  )
}

function DetailHeader({ project }: DetailHeaderProps): ReactElement {
  const { t } = useTranslation()
  const history = useHistory()
  return (
    <Container>
      <Right>
        <ProjectName>{project.name}</ProjectName>
        <Status>
          {/* FIXME */}
          <div className="text">连接检查中</div>
        </Status>
      </Right>
      <Left>
        <HeaderAction>
          <CheckConnection />
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
                  history.push({
                    pathname: '/edit-project',
                    state: {
                      project,
                    },
                  })
                }}
              />
            }
          />
        </HeaderAction>
      </Left>
    </Container>
  )
}

export default DetailHeader
