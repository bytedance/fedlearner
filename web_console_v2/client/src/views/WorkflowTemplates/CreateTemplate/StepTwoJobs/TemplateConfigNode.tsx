import React, { FC } from 'react';
import { Handle, Position } from 'react-flow-renderer';
import {
  Container,
  JobName,
  JobStatusText,
  StatusIcon,
} from 'components/WorkflowJobsCanvas/JobNodes/styles';
import {
  configStatusText,
  JobNodeProps,
  statusIcons,
  WORKFLOW_JOB_NODE_CHANNELS,
} from 'components/WorkflowJobsCanvas/JobNodes/shared';
import { NodeData } from 'components/WorkflowJobsCanvas/types';
import GridRow from 'components/_base/GridRow';
import classNames from 'classnames';
import { PlusCircle } from 'components/IconPark';
import styled from 'styled-components';
import { MixinCircle, MixinCommonTransition, MixinFlexAlignCenter } from 'styles/mixins';
import PubSub from 'pubsub-js';
import { Tooltip } from 'antd';
import { getOrInsertValueByid } from 'views/WorkflowTemplates/CreateTemplate/store';

const AddJobButton = styled.div`
  ${MixinCircle(20)}
  ${MixinFlexAlignCenter()}
  ${MixinCommonTransition()}
  position: absolute;
  display: flex;
  background-color: white;
  color: var(--textColorDisabled);
  font-size: 20px;

  &:hover {
    color: var(--primaryColor);
    border-color: currentColor;
  }

  &::before {
    content: '';
    position: absolute;
    height: 21px;
    padding: 10px 0;
    width: 13px;
    background-color: currentColor;
    background-clip: content-box;
  }

  &.left {
    left: -32px;
    top: calc(50% - 12px);

    &::before {
      right: -11px;
    }
  }
  &.right {
    right: -32px;
    top: calc(50% - 12px);

    &::before {
      left: -11px;
    }
  }
  &.bottom {
    bottom: -32px;
    left: calc(50% - 12px);

    &::before {
      top: -15px;
      transform: rotate(90deg);
    }
  }
`;
const StyledContainer = styled(Container)`
  &:hover {
    z-index: 5;
  }
  &:not(:hover) {
    .${AddJobButton.styledComponentId} {
      opacity: 0;
    }
  }
`;

type AddPosition = 'left' | 'right' | 'bottom';
const AddJobHandle: FC<{ position: AddPosition; onClick: any }> = ({ position, onClick }) => {
  return (
    <Tooltip title="Click to add a new job">
      <AddJobButton className={position} onClick={onButtonClick}>
        <PlusCircle />
      </AddJobButton>
    </Tooltip>
  );

  function onButtonClick(event: React.SyntheticEvent<any>) {
    onClick && onClick(position);

    event.stopPropagation();
  }
};

export type AddJobPayload = {
  id: string;
  data: NodeData;
  position: AddPosition;
};

const TemplateConfigNode: FC<JobNodeProps> = ({ data, id }) => {
  const icon = statusIcons[data.status];
  const text = configStatusText[data.status];

  const values = getOrInsertValueByid(id);

  return (
    <StyledContainer className={classNames([data.raw.is_federated && 'federated-mark', data.mark])}>
      <Handle type="target" position={Position.Top} />

      <JobName data-secondary={Boolean(values?.name)}>{values?.name || '// 点击配置'}</JobName>

      <GridRow gap={5}>
        {icon && <StatusIcon src={icon} />}
        <JobStatusText>{text}</JobStatusText>
      </GridRow>

      <AddJobHandle position="left" onClick={onAddJobClick} />
      <AddJobHandle position="right" onClick={onAddJobClick} />
      <AddJobHandle position="bottom" onClick={onAddJobClick} />

      <Handle type="source" position={Position.Bottom} />
    </StyledContainer>
  );

  function onAddJobClick(position: AddPosition) {
    PubSub.publish(WORKFLOW_JOB_NODE_CHANNELS.click_add_job, {
      id,
      data,
      position,
    } as AddJobPayload);
  }
};

export default TemplateConfigNode;
