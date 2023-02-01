import React, { FC } from 'react';
import { Handle, Position } from 'react-flow-renderer';

import { GlobalConfigNodeContainer, JobName, JobStatusText, StatusIcon } from './elements';
import { configStatusText, GlobalNodeProps, statusIcons } from './shared';
import GridRow from 'components/_base/GridRow';

const GlobalConfigNode: FC<GlobalNodeProps> = ({ data, id }) => {
  const icon = statusIcons[data.status];
  const text = configStatusText[data.status];

  return (
    <GlobalConfigNodeContainer>
      <Handle type="target" position={Position.Top} />
      <JobName>{data.raw.name}</JobName>
      <GridRow gap={5}>
        {icon && <StatusIcon src={icon} />}
        <JobStatusText>{text}</JobStatusText>
      </GridRow>
      <Handle type="source" position={Position.Bottom} />
    </GlobalConfigNodeContainer>
  );
};

export default GlobalConfigNode;
