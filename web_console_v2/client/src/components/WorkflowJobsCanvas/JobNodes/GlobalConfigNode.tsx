import React, { FC } from 'react';
import { GlobalConfigNodeContainer, JobName, JobStatusText, StatusIcon } from './styles';
import { configStatusText, GlobalNodeProps, statusIcons } from './shared';
import GridRow from 'components/_base/GridRow';

const GlobalConfigNode: FC<GlobalNodeProps> = ({ data, id }) => {
  const icon = statusIcons[data.status];
  const text = configStatusText[data.status];

  return (
    <GlobalConfigNodeContainer>
      <JobName>{data.raw.name}</JobName>
      <GridRow gap={5}>
        {icon && <StatusIcon src={icon} />}
        <JobStatusText>{text}</JobStatusText>
      </GridRow>
    </GlobalConfigNodeContainer>
  );
};

export default GlobalConfigNode;
