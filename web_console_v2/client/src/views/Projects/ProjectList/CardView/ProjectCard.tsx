import React, { FC, ReactElement } from 'react';
import styled from 'styled-components';
import ProjectProp from './ProjectCardProp';
import ProjectMoreActions from '../../ProjectMoreActions';
import CreateTime from '../../CreateTime';
import { Tooltip, Row } from 'antd';
import { useTranslation } from 'react-i18next';
import ProjectName from '../../ProjectName';
import { useHistory } from 'react-router-dom';
import { Project } from 'typings/project';
import ProjectConnectionStatus from '../../ConnectionStatus';
import { MixinCommonTransition, MixinFontClarity } from 'styles/mixins';
import { Command, Workbench } from 'components/IconPark';
import IconButton from 'components/IconButton';
import { useCheckConnection } from 'hooks/project';

const CardContainer = styled.div`
  ${MixinCommonTransition('box-shadow')}

  border: 1px solid var(--backgroundGray);
  border-radius: 4px;
  overflow: hidden; // Prevent card from expanding grid

  &:hover {
    box-shadow: 0px 4px 10px var(--gray2);
  }
`;
const CardHeader = styled.div`
  display: flex;
  height: 40px;
  border-bottom: 1px solid var(--backgroundGray);
  justify-content: space-between;
  cursor: pointer;

  @supports (gap: 10px) {
    gap: 10px;
  }
`;

const CardMain = styled.div`
  display: flex;
  padding: 25px 0;
  cursor: pointer;

  .workflow-number {
    ${MixinFontClarity()}

    font-size: 32px;
    text-indent: 1px;
    line-height: 1;
    color: var(--textColorStrong);
  }
`;
const CardFooter = styled(Row)`
  padding: 12px 10px;

  .left {
    flex: 1;
    font-size: 12px;
    line-height: 22px;
    color: var(--gray7);
    padding-left: 6px;
  }
  .right {
    display: flex;
    min-width: 80px;
    justify-content: space-between;
  }
`;

interface CardProps {
  item: Project;
  onViewDetail: (project: Project) => void;
}

type IconButtonProps = {
  onClick: Function;
};

const CreateWorkflow: FC<IconButtonProps> = ({ onClick }) => {
  const { t } = useTranslation();

  return (
    <Tooltip title={t('project.create_work_flow')} placement="top">
      <IconButton onClick={onClick as any} icon={<Workbench />} circle />
    </Tooltip>
  );
};

const CheckConnection: FC<IconButtonProps> = ({ onClick }) => {
  const { t } = useTranslation();

  return (
    <Tooltip title={t('project.check_connection')} placement="top">
      <IconButton onClick={onClick as any} icon={<Command />} circle />
    </Tooltip>
  );
};

function Card({ item: project, onViewDetail }: CardProps): ReactElement {
  const { t } = useTranslation();
  const history = useHistory();
  const [status, checkConnection] = useCheckConnection(project);

  const participant = project.config.participants[0].name || '-';

  return (
    <CardContainer>
      <CardHeader onClick={viewDetail}>
        <ProjectName text={project.name} />
        <CreateTime time={project.created_at} />
      </CardHeader>

      <CardMain onClick={viewDetail}>
        <ProjectProp label={t('project.workflow_number')}>
          <strong className="workflow-number">{project.num_workflow || 0}</strong>
        </ProjectProp>

        <ProjectProp label={t('project.connection_status')}>
          <ProjectConnectionStatus status={status} />
        </ProjectProp>
      </CardMain>

      <CardFooter align="middle">
        <div className="left">{participant}</div>
        <div className="right">
          <CheckConnection onClick={checkConnection} />
          <CreateWorkflow onClick={initiateWorkflow} />

          <ProjectMoreActions
            onEdit={() => {
              history.push(`/projects/edit/${project.id}`);
            }}
            onViewDetail={viewDetail}
          />
        </div>
      </CardFooter>
    </CardContainer>
  );

  function viewDetail() {
    onViewDetail(project);
  }
  function initiateWorkflow() {
    history.push(`/workflows/initiate/basic?project=${project.id}`);
  }
}

export default Card;
