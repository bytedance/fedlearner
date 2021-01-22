import React, { ReactElement, useState } from 'react';
import styled, { CSSProperties } from 'styled-components';
import { Project } from 'typings/project';
import ProjectConnectionStatus from '../../ConnectionStatus';
import CreateTime from '../../CreateTime';
import ProjectName from '../../ProjectName';
import ProjectMoreActions from '../../ProjectMoreActions';
import { Link, useHistory } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from 'antd';
import GridRow from 'components/_base/GridRow';

const Container = styled.div`
  display: flex;
  width: 100%;
  height: 60px;
  align-items: center;
  padding: 0 16px;

  &:not(:last-of-type) {
    border-bottom: 1px solid var(--darkGray10);
  }
`;

const ContainerItem = styled.div`
  flex: 1;
  overflow: hidden;
  .project-connection-status {
    line-height: 50px;
  }
`;

const Cell = styled.div`
  font-size: 13px;
`;

interface TableItemProps {
  tableConfigs: {
    i18nKey: string;
    width: number;
  }[];
  item: Project;
  onViewDetail: (project: Project) => void;
}

function Action({ project, onViewDetail }: any): ReactElement {
  const { t } = useTranslation();
  const history = useHistory();

  return (
    <GridRow style={{ marginLeft: '-12px' }}>
      <Button size="small" type="link">
        {t('project.check_connection')}
      </Button>
      <Button size="small" type="link">
        {t('project.create_work_flow')}
      </Button>

      <ProjectMoreActions
        style={{ marginTop: '13px' }}
        onEdit={() => {
          history.push(`/projects/edit/${project.id}`);
        }}
        onViewDetail={() => onViewDetail(project)}
      />
    </GridRow>
  );
}

const getCellContent = ({
  project,
  i18nKey,
  onViewDetail,
}: {
  i18nKey: string;
  project: Project;
  onViewDetail: (project: Project) => void;
}) => {
  switch (i18nKey) {
    case 'project.name':
      return <Button onClick={() => onViewDetail(project)}>{project.name}</Button>;
    case 'project.workflow_number':
      return <Cell>{project.num_workflow}</Cell>;
    case 'project.creator':
      return <Cell>{project.config.participants[0].name}</Cell>;
    case 'project.creat_time':
      return (
        <CreateTime time={project.created_at} style={{ lineHeight: '50px', color: '#1A2233' }} />
      );
    case 'operation':
      return <Action project={project} onViewDetail={onViewDetail} />;
    default:
      return null as never;
  }
};

function TableItem({ tableConfigs, item: project, onViewDetail }: TableItemProps): ReactElement {
  return (
    <Container>
      {tableConfigs.map((item) => (
        <ContainerItem style={{ flex: item.width }} key={item.i18nKey}>
          {getCellContent({ i18nKey: item.i18nKey, project, onViewDetail })}
        </ContainerItem>
      ))}
    </Container>
  );
}

export default TableItem;
