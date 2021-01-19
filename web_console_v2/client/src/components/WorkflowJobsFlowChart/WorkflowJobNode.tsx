import React, { FC } from 'react';
import { Handle, NodeComponentProps, Position } from 'react-flow-renderer';
import styled from 'styled-components';
import pendingIcon from 'assets/icons/workflow-pending.svg';
import completetdIcon from 'assets/icons/workflow-completed.svg';
import warningIcon from 'assets/icons/workflow-warning.svg';
import errorIcon from 'assets/icons/workflow-error.svg';
import GridRow from 'components/_base/GridRow';
import { JobNodeData, JobNodeStatus, JobNodeType } from './helpers';
import i18n from 'i18n';

const Container = styled.div``;
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

const WorkflowJobNode: Record<JobNodeType, FC<Props>> = {
  config: ConfigJobNode,
  execution: ExecutionJobNode,
};

export default WorkflowJobNode;
