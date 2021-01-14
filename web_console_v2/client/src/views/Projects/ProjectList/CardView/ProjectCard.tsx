import React, { FC, ReactElement, useState } from 'react';
import styled from 'styled-components';
import ProjectProp from './ProjectCardProp';
import ProjectMoreActions from '../../ProjectMoreActions';
import CreateTime from '../../CreateTime';
import ProjectDetailDrawer from '../../ProjectDetailDrawer';
import { Tooltip, Row } from 'antd';
import { useTranslation } from 'react-i18next';
import { ReactComponent as CheckConnectionIcon } from 'assets/images/check-connect.svg';
import initiateAWorkflow from 'assets/images/create-work-flow.svg';
import ProjectName from '../../ProjectName';
import { useHistory } from 'react-router-dom';
import { Project } from 'typings/project';
import ProjectConnectionStatus from '../../ConnectionStatus';
import { MixinCommonTransition, MixinFontClarity } from 'styles/mixins';

const CardContainer = styled.div`
  ${MixinCommonTransition('box-shadow')}

  border: 1px solid var(--gray3);
  border-radius: 4px;
  overflow: hidden; // Prevent card from expanding grid

  &:hover {
    box-shadow: 0px 4px 10px var(--gray2);
  }
`;
const CardHeaderContainer = styled.div`
  display: flex;
  height: 40px;
  border-bottom: 1px solid var(--gray3);
  justify-content: space-between;
  cursor: pointer;
  gap: 10px;
`;
const CardMainContainer = styled.div`
  display: flex;
  padding: 25px 0;

  .workflow-number {
    ${MixinFontClarity()}

    font-size: 32px;
    text-indent: 1px;
    color: var(--textColorStrong);
  }
`;
const CardFooterContainer = styled(Row)`
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
const CheckConnectionStyle = styled.div`
  height: 24px;
  width: 24px;
  padding: 2px 6px 0;
  border-radius: 12px;
  cursor: pointer;
  path {
    stroke: #4e4f69;
  }
  &:hover {
    background-color: var(--gray1);
    path {
      stroke: var(--primaryColor);
    }
  }
`;

interface CardProps {
  item: Project;
}

interface CardHeaderProps {
  name: string;
  time: number;
}

interface CardMainProps {
  workFlowNumber: number;
  connectionStatus: number;
}

type SharedProps = {
  project: Project;
};

function CardHeader({ name, time }: CardHeaderProps): ReactElement {
  return (
    <CardHeaderContainer>
      <ProjectName text={name} />
      <CreateTime time={time} />
    </CardHeaderContainer>
  );
}

function CardMain({ workFlowNumber }: CardMainProps): ReactElement {
  //FIXME
  const random: number = Math.random() * 3.99;
  const connectionStatus = Math.floor(random);
  const { t } = useTranslation();

  return (
    <CardMainContainer>
      <ProjectProp label={t('project.workflow_number')}>
        <strong className="workflow-number">{workFlowNumber}</strong>
      </ProjectProp>

      <ProjectProp label={t('project.connection_status')}>
        <ProjectConnectionStatus connectionStatus={connectionStatus} />
      </ProjectProp>
    </CardMainContainer>
  );
}

const CreateWorkflow: FC<SharedProps> = ({ project }) => {
  const { t } = useTranslation();
  const history = useHistory();
  return (
    <Tooltip title={t('project.create_work_flow')} placement="top">
      <img
        onClick={goinitiateAWorkflow}
        src={initiateAWorkflow}
        style={{ cursor: 'pointer' }}
        alt=""
      />
    </Tooltip>
  );

  function goinitiateAWorkflow() {
    history.push(`/workflows/initiate/basic?project=${project.id}`);
  }
};

const CheckConnection: FC<SharedProps> = () => {
  const { t } = useTranslation();
  return (
    <Tooltip title={t('project.check_connection') + ' (Not ready yet)'} placement="top">
      <CheckConnectionStyle>
        <CheckConnectionIcon />
      </CheckConnectionStyle>
    </Tooltip>
  );
};

const CardFooter: FC<SharedProps> = ({ project }) => {
  const history = useHistory();
  const [isDrawerVisible, setIsDrawerVisible] = useState(false);

  const participant = project.config.participants[0].name || '-';

  return (
    <CardFooterContainer align="middle">
      <div className="left">{participant}</div>
      <div className="right">
        <CheckConnection project={project} />
        <CreateWorkflow project={project} />

        <ProjectMoreActions
          onEdit={() => {
            history.push({
              pathname: '/projects/edit',
              state: {
                project,
              },
            });
          }}
          onViewDetail={() => setIsDrawerVisible(true)}
        />
      </div>
      <ProjectDetailDrawer
        title={project.name}
        project={project}
        onClose={() => setIsDrawerVisible(false)}
        visible={isDrawerVisible}
      />
    </CardFooterContainer>
  );
};

function Card({ item }: CardProps): ReactElement {
  return (
    <CardContainer>
      <CardHeader name={item.name} time={item.created_at} />
      {/* FIXME: remove connection status mock */}
      <CardMain workFlowNumber={item.workflow_num} connectionStatus={1} />
      <CardFooter project={item} />
    </CardContainer>
  );
}

export default Card;
