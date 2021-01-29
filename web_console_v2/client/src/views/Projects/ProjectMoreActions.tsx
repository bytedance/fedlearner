import React, { ReactElement } from 'react';
import styled, { CSSProperties } from 'styled-components';
import { useTranslation } from 'react-i18next';
import { Popover } from 'antd';
import IconButton from 'components/IconButton';
import { More } from 'components/IconPark';

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
    >
      <IconButton type="text" icon={<More />} circle />
    </Popover>
  );
}

export default ProjectMoreActions;
