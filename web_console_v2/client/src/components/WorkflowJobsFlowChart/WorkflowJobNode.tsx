import React, { FC, useState } from 'react';
import { Handle, NodeComponentProps, Position } from 'react-flow-renderer';
import { Dropdown, Menu, Modal } from 'antd';
import { MenuInfo } from 'rc-menu/lib/interface';
import styled from 'styled-components';
import pendingIcon from 'assets/icons/workflow-pending.svg';
import completetdIcon from 'assets/icons/workflow-completed.svg';
import warningIcon from 'assets/icons/workflow-warning.svg';
import errorIcon from 'assets/icons/workflow-error.svg';
import GridRow from 'components/_base/GridRow';
import {
  NodeData,
  JobNodeStatus,
  ChartNodeType,
  NODE_HEIGHT,
  NODE_WIDTH,
  GLOBAL_CONFIG_NODE_SIZE,
} from './helpers';
import { convertToUnit } from 'shared/helpers';
import i18n from 'i18n';
import classNames from 'classnames';
import { Down } from 'components/IconPark';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';

const Container = styled.div`
  position: relative;
  width: ${convertToUnit(NODE_WIDTH)};
  height: ${convertToUnit(NODE_HEIGHT)};
  background-color: var(--selected-background, white);
  border: 1px solid var(--selected-border-color, transparent);
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
  justify-content: center;
  align-items: center;
  width: ${convertToUnit(GLOBAL_CONFIG_NODE_SIZE)};
  height: ${convertToUnit(GLOBAL_CONFIG_NODE_SIZE)};
  border-radius: 50%;
  background-color: var(--selected-background, white);
  border: 1px solid var(--selected-border-color, transparent);
`;
const InheritButton = styled.div`
  position: absolute;
  bottom: 21px;
  right: 14px;
  display: flex;
  align-items: center;
  line-height: 1;
  font-size: 12px;
  color: var(--primaryColor);
`;
const ArrowDown = styled(Down)`
  margin-left: 5px;
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
  data: NodeData;
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

const ForkJobNode: FC<Props> = ({ data, id }) => {
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
      <Dropdown
        overlay={
          <Menu>
            <Menu.Item key="0" onClick={(e) => changeInheritance(e, true)}>
              继承
            </Menu.Item>
            <Menu.Item key="1" onClick={(e) => changeInheritance(e, false)}>
              不继承
            </Menu.Item>
          </Menu>
        }
      >
        <InheritButton onClick={(e) => e.stopPropagation()}>
          {data.inherit ? '继承' : '不继承'} <ArrowDown />
        </InheritButton>
      </Dropdown>
      {data.isSource && <Handle type="source" position={Position.Bottom} />}
    </Container>
  );

  function changeInheritance(event: MenuInfo, isInherit: boolean) {
    event.domEvent.stopPropagation();

    if (isInherit === data.inherit) {
      return;
    }

    Modal.confirm({
      title: `切换至${isInherit ? '继承' : '不继承'}状态`,
      zIndex: Z_INDEX_GREATER_THAN_HEADER,
      icon: null,
      content: isInherit
        ? `${id} 改为继承状态后，后续依赖 ${id} 的任务都将重置为“继承”状态`
        : `${id} 改为不继承状态后，后续依赖 ${id} 的任务都将切换成为“不继承”状态`,

      mask: false,
      style: {
        top: '35%',
      },
      onOk() {
        // TODO: broadcast inheritance change
      },
    });
  }
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

const GlobalConfigNode: FC<Props> = ({ data, id }) => {
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

const WorkflowJobNode: Record<ChartNodeType, FC<Props>> = {
  fork: ForkJobNode,
  config: ConfigJobNode,
  global: GlobalConfigNode,
  execution: ExecutionJobNode,
};

export default WorkflowJobNode;
