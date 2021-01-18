import React, { ReactElement } from 'react';
import styled, { CSSProperties } from 'styled-components';
import { useTranslation } from 'react-i18next';
import action from 'assets/images/project-action.svg';
import { Popover } from 'antd';

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
    cursor: pointer;
    &:hover {
      background-color: var(--gray1);
    }
  }
`;

const ActionStyle = styled.div`
  height: 24px;
  display: flex;
  cursor: pointer;
  .aciton-icon {
    height: 24px;
    width: 24px;
    padding: 10px 4px;
  }
`;

interface ProjectMoreActionsProps {
  suffix?: React.ReactNode;
  actionList?: React.ReactNode;
  onEdit?: () => void;
  onViewDetail?: () => void;
  style?: CSSProperties;
}

function ActionList({ onEdit, onViewDetail }: ProjectMoreActionsProps): ReactElement {
  const { t } = useTranslation();
  return (
    <ActionListContainer>
      <div className="actionItem" onClick={onEdit}>
        {t('project.action_edit')}
      </div>
      <div className="actionItem" onClick={onViewDetail}>
        {t('project.action_detail')}
      </div>
    </ActionListContainer>
  );
}

function ProjectMoreActions(props: ProjectMoreActionsProps): ReactElement {
  return (
    <Popover
      content={props.actionList ?? <ActionList {...props} />}
      placement="bottomLeft"
      overlayClassName="project-actions"
      getPopupContainer={(node) => node}
    >
      <ActionStyle style={props.style}>
        <img src={action} className="aciton-icon" alt="" />
        {props.suffix ?? null}
      </ActionStyle>
    </Popover>
  );
}

export default ProjectMoreActions;
