import React, { FC } from 'react';
import { Handle, Position } from 'react-flow-renderer';
import { Container, JobName, JobStatusText, StatusIcon, InheritedTag } from './styles';
import { executionStatusText, JobNodeProps, statusIcons } from './shared';
import GridRow from 'components/_base/GridRow';
import classNames from 'classnames';

const ExecutionJobNode: FC<JobNodeProps> = ({ data, id }) => {
  const icon = statusIcons[data.status];
  const text = executionStatusText[data.status];

  return (
    <Container className={classNames([data.raw.is_federated && 'federated-mark', data.mark])}>
      {data.isTarget && <Handle type="target" position={Position.Top} />}
      <JobName>{id}</JobName>
      <GridRow gap={5}>
        {icon && <StatusIcon src={icon} />}
        <JobStatusText>{text}</JobStatusText>

        {data.raw.inherited && <InheritedTag color="orange">已继承</InheritedTag>}
      </GridRow>
      {data.isSource && <Handle type="source" position={Position.Bottom} />}
    </Container>
  );
};

export default ExecutionJobNode;
