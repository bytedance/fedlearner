import React, { ReactElement, useState } from 'react'
import styled from 'styled-components'
import { useTranslation } from 'react-i18next'
import action from 'assets/images/project-action.svg'
import { Popover } from 'antd'

const ActionListContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 74px;
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

const ActionStyle = styled.div`
  height: 24px;
  width: 24px;
  padding: 10px 4px;
  .aciton-icon {
    height: 4px;
    width: 16px;
  }
`

interface ProjectActionProps {
  onEdit: () => void
  onDetail: () => void
}


function ActionList(props: ProjectActionProps): ReactElement {
  const { t } = useTranslation()
  return (
    <ActionListContainer>
      <div className="actionItem" onClick={props.onEdit}>{t('project_action_edit')}</div>
      <div className="actionItem" onClick={props.onDetail}>{t('project_action_detail')}</div>
    </ActionListContainer>
  )
}

function ProjectAction(props: ProjectActionProps): ReactElement {
  return (
    <Popover content={<ActionList {...props}/>} placement="bottomLeft" overlayClassName="project-actions">
      <ActionStyle>
        <img src={action} className="aciton-icon" alt="" />
      </ActionStyle>
    </Popover>
  )
}



export default ProjectAction
