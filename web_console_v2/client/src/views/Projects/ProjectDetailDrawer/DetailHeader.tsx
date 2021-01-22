import React, { ReactElement } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { useHistory } from 'react-router-dom';
import { Project } from 'typings/project';
import ProjectConnectionStatus from '../ConnectionStatus';
import { useCheckConnection } from 'hooks/project';
import GridRow from 'components/_base/GridRow';
import { Button, Row } from 'antd';
import { Command, Workbench } from 'components/IconPark';

const RowContainer = styled(Row)`
  padding-right: 28px;
`;

const ProjectName = styled.div`
  font-weight: 500;
  font-size: 20px;
  line-height: 28px;
  color: var(--textColor);
`;

interface Props {
  project: Project;
}

function DetailHeader({ project }: Props): ReactElement {
  const { t } = useTranslation();
  const history = useHistory();
  const [status, checkConnection] = useCheckConnection(project);

  return (
    <RowContainer justify="space-between" align="middle">
      <GridRow gap="10">
        <ProjectName>{project.name}</ProjectName>
        <ProjectConnectionStatus status={status} tag />
      </GridRow>
      <GridRow gap="10">
        <Button size="small" icon={<Command />} onClick={checkConnection as any}>
          {t('project.check_connection')}
        </Button>
        <Button
          size="small"
          icon={<Workbench />}
          onClick={() => history.push(`/workflows/initiate/basic?project=${project.id}`)}
        >
          {t('project.create_work_flow')}
        </Button>
      </GridRow>
    </RowContainer>
  );
}

export default DetailHeader;
