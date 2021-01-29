import React, { FC } from 'react';
import { Handle, NodeComponentProps, Position } from 'react-flow-renderer';
import styled from 'styled-components';
import pendingIcon from 'assets/icons/workflow-pending.svg';
import completetdIcon from 'assets/icons/workflow-completed.svg';
import warningIcon from 'assets/icons/workflow-warning.svg';
import errorIcon from 'assets/icons/workflow-error.svg';
import GridRow from 'components/_base/GridRow';
import {
  JobNodeData,
  JobNodeStatus,
  JobNodeType,
  NODE_HEIGHT,
  NODE_WIDTH,
  GLOBAL_CONFIG_NODE_SIZE,
} from './helpers';
import { convertToUnit } from 'shared/helpers';
import i18n from 'i18n';
import classNames from 'classnames';

const Container = styled.div`
  position: relative;
  width: ${convertToUnit(NODE_WIDTH)};
  height: ${convertToUnit(NODE_HEIGHT)};
  padding: 14px 20px;
  border-radius: 4px;

  &.federated-mark {
    box-shadow: 6px 0 0 -2px var(--fed-color, transparent) inset;
  }

  &.blue {
    --fed-color: var(--primaryColor);
  }
  &.green {
    --fed-color: var(--successColor);
  }
  &.yellow {
    --fed-color: var(--darkGold6);
  }
  &.magenta {
    --fed-color: var(--magenta5);
  }
  &.cyan {
    --fed-color: var(--cyan6);
  }
`;
const JobName = styled.h5`
  font-size: 16px;
  line-height: 20px;
  white-space: nowrap;
  color: var(--textColorStrong);
`;
const StatusIcon = styled.img`
  display: block;
  width: 16px;
  height: 16px;
`;
const JobStatusText = styled.small`
  font-size: 13px;
  line-height: 1;
  color: var(--textColorSecondary);
`;
const GlobalConfigNodeContainer = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: ${convertToUnit(GLOBAL_CONFIG_NODE_SIZE)};
  height: ${convertToUnit(GLOBAL_CONFIG_NODE_SIZE)};
  border-radius: 50%;
`;

const statusIcons: Record<JobNodeStatus, string> = {
  [JobNodeStatus.Pending]: '',
  [JobNodeStatus.Processing]: pendingIcon,
  [JobNodeStatus.Success]: completetdIcon,
  [JobNodeStatus.Warning]: warningIcon,
  [JobNodeStatus.Error]: errorIcon,
};

const jobConfigStatusText: Record<JobNodeStatus, string> = {
  [JobNodeStatus.Pending]: i18n.t('workflow.job_node_pending'),
  [JobNodeStatus.Processing]: i18n.t('workflow.job_node_configuring'),
  [JobNodeStatus.Success]: i18n.t('workflow.job_node_config_completed'),
  [JobNodeStatus.Warning]: i18n.t('workflow.job_node_unfinished'),
  [JobNodeStatus.Error]: '',
};

export const jobExecutionStatusText: Record<JobNodeStatus, string> = {
  [JobNodeStatus.Pending]: i18n.t('workflow.job_node_waiting'),
  [JobNodeStatus.Processing]: i18n.t('workflow.job_node_running'),
  [JobNodeStatus.Success]: i18n.t('workflow.job_node_success'),
  [JobNodeStatus.Warning]: i18n.t('workflow.job_node_failed'),
  [JobNodeStatus.Error]: i18n.t('workflow.job_node_stop_running'),
};

interface Props extends NodeComponentProps {
  data: JobNodeData;
}

const ConfigJobNode: FC<Props> = ({ data, id }) => {
  const icon = statusIcons[data.status];
  const text = jobConfigStatusText[data.status];

  return (
    <Container>
      {data.isTarget && <Handle type="target" position={Position.Top} />}
      <JobName>{id}</JobName>
      <GridRow gap={5}>
        {icon && <StatusIcon src={icon} />}
        <JobStatusText>{text}</JobStatusText>
      </GridRow>
      {data.isSource && <Handle type="source" position={Position.Bottom} />}
    </Container>
  );
};

const ExecutionJobNode: FC<Props> = ({ data, id }) => {
  const icon = statusIcons[data.status];
  const text = jobExecutionStatusText[data.status];

  return (
    <Container className={classNames([data.raw.is_federated && 'federated-mark', data.mark])}>
      {data.isTarget && <Handle type="target" position={Position.Top} />}
      <JobName>{id}</JobName>
      <GridRow gap={5}>
        {icon && <StatusIcon src={icon} />}
        <JobStatusText>{text}</JobStatusText>
      </GridRow>
      {data.isSource && <Handle type="source" position={Position.Bottom} />}
    </Container>
  );
};

const GlobalJobNode: FC<Props> = ({ data, id }) => {
  const icon = statusIcons[data.status];
  const text = jobConfigStatusText[data.status];

  return (
    <GlobalConfigNodeContainer>
      <JobName>{id}</JobName>
      <GridRow gap={5}>
        {icon && <StatusIcon src={icon} />}
        <JobStatusText>{text}</JobStatusText>
      </GridRow>
    </GlobalConfigNodeContainer>
  );
};

const WorkflowJobNode: Record<JobNodeType, FC<Props>> = {
  config: ConfigJobNode,
  global: GlobalJobNode,
  execution: ExecutionJobNode,
};

export default WorkflowJobNode;
