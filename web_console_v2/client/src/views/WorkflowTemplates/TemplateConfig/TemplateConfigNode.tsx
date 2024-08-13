import React, { FC } from 'react';
import { Handle, Position } from 'react-flow-renderer';
import {
  Container,
  JobName,
  JobStatusText,
  StatusIcon,
} from 'components/WorkflowJobsCanvas/JobNodes/elements';
import {
  configStatusText,
  JobNodeProps,
  statusIcons,
  WORKFLOW_JOB_NODE_CHANNELS,
} from 'components/WorkflowJobsCanvas/JobNodes/shared';
import { ChartNodeStatus, NodeData } from 'components/WorkflowJobsCanvas/types';
import GridRow from 'components/_base/GridRow';
import classNames from 'classnames';
import { PlusCircle } from 'components/IconPark';
import styled from './TemplateConfigNode.module.less';
import PubSub from 'pubsub-js';
import { Tooltip } from '@arco-design/web-react';
import { definitionsStore } from 'views/WorkflowTemplates/TemplateForm/stores';
import { IconLoading } from '@arco-design/web-react/icon';

const detailRegx = /detail/g;
const isCheck = detailRegx.test(window.location.href);

type AddPosition = 'left' | 'right' | 'bottom';
const AddJobHandle: FC<{ position: AddPosition; onClick: any }> = ({ position, onClick }) => {
  let _position = '';
  switch (position) {
    case 'left':
      _position = styled.left;
      break;
    case 'right':
      _position = styled.right;
      break;
    case 'bottom':
      _position = styled.bottom;
      break;
    default:
      _position = styled.bottom;
      break;
  }
  return (
    <Tooltip content={`Click to add a new job to ${position}`}>
      <div
        className={classNames([styled.add_job_button, _position])}
        style={{ pointerEvents: 'auto' }}
        onClick={onButtonClick}
      >
        <PlusCircle />
      </div>
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

const NodeStatus: FC<{ status: ChartNodeStatus }> = ({ status }) => {
  // node status is success in detail page
  const icon = statusIcons[status];
  const text = configStatusText[status];

  const isValidating = status === ChartNodeStatus.Validating;

  return isValidating ? (
    <GridRow gap={5}>
      <IconLoading style={{ fontSize: 16, color: 'var(--primaryColor)' }} />
      <JobStatusText>{text}</JobStatusText>
    </GridRow>
  ) : (
    <GridRow gap={5}>
      {icon && <StatusIcon src={icon} />}

      <JobStatusText>{text}</JobStatusText>
    </GridRow>
  );
};

const TemplateConfigNode: FC<JobNodeProps> = ({ data, id }) => {
  const values = definitionsStore.getValueById(id);
  return (
    <Container
      data-uuid={data.raw.uuid}
      className={classNames([
        data.raw.is_federated && 'federated-mark',
        data.mark,
        styled.container,
      ])}
    >
      <Handle type="target" position={Position.Top} />

      <JobName data-secondary={Boolean(values?.name)}>{values?.name || '//点击配置'}</JobName>

      <NodeStatus key={data.status} status={data.status} />

      {!isCheck && (
        <>
          <AddJobHandle position="left" onClick={onAddJobClick} />
          <AddJobHandle position="right" onClick={onAddJobClick} />
          <AddJobHandle position="bottom" onClick={onAddJobClick} />
        </>
      )}

      <Handle type="source" position={Position.Bottom} />
    </Container>
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
