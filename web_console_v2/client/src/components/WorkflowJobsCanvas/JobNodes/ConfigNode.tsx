import React, { FC } from 'react';
import { Handle, Position } from 'react-flow-renderer';
import { Container, JobName, JobStatusText, StatusIcon } from './styles';
import { configStatusText, JobNodeProps, statusIcons } from './shared';
import GridRow from 'components/_base/GridRow';

const ConfigJobNode: FC<JobNodeProps> = ({ data, id }) => {
  const icon = statusIcons[data.status];
  const text = configStatusText[data.status];

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

export default ConfigJobNode;
