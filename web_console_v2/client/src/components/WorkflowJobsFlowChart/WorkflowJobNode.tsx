import React, { FC } from 'react';
import { Handle, NodeComponentProps, Position } from 'react-flow-renderer';
import { Dropdown, Menu, Modal } from 'antd';
import { MenuInfo } from 'rc-menu/lib/interface';
import styled from 'styled-components';
import pendingIcon from 'assets/icons/workflow-pending.svg';
import completetdIcon from 'assets/icons/workflow-completed.svg';
import warningIcon from 'assets/icons/workflow-warning.svg';
import errorIcon from 'assets/icons/workflow-error.svg';
import GridRow from 'components/_base/GridRow';
import { NODE_HEIGHT, NODE_WIDTH, GLOBAL_CONFIG_NODE_SIZE } from './helpers';
import { NodeData, JobNodeStatus, ChartNodeType } from './types';
import { convertToUnit } from 'shared/helpers';
import i18n from 'i18n';
import classNames from 'classnames';
import { Down } from 'components/IconPark';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import PubSub from 'pubsub-js';
import { useTranslation } from 'react-i18next';

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
  bottom: 11px;
  right: 14px;
  display: flex;
  align-items: center;
  padding-bottom: 5px;
  line-height: 1.8;
  font-size: 12px;
  color: var(--primaryColor);

  &[data-inherit='false'] {
    color: var(--warningColor);
  }
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

export const WORKFLOW_JOB_NODE_CHANNELS = {
  change_inheritance: 'job_node.change_inheritance',
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
  const { t } = useTranslation();
  const icon = statusIcons[data.status];
  const text = jobConfigStatusText[data.status];

  const labelReusable = t('workflow.label_job_reuseable');
  const labelNonreusable = t('workflow.label_job_nonreusable');

  return (
    <Container
      data-inherit={data.inherit!.toString()}
      className={classNames([data.raw.is_federated && 'federated-mark', data.mark])}
    >
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
              {labelReusable}
            </Menu.Item>
            <Menu.Item key="1" onClick={(e) => changeInheritance(e, false)}>
              {labelNonreusable}
            </Menu.Item>
          </Menu>
        }
      >
        <InheritButton data-inherit={data.inherit!.toString()} onClick={(e) => e.stopPropagation()}>
          {data.inherit ? labelReusable : labelNonreusable} <ArrowDown />
        </InheritButton>
      </Dropdown>
      {data.isSource && <Handle type="source" position={Position.Bottom} />}
    </Container>
  );

  function changeInheritance(event: MenuInfo, whetherInherit: boolean) {
    event.domEvent.stopPropagation();

    if (whetherInherit === data.inherit) {
      return;
    }

    Modal.confirm({
      title: t('workflow.title_toggle_reusable', {
        state: whetherInherit ? labelReusable : labelNonreusable,
      }),
      zIndex: Z_INDEX_GREATER_THAN_HEADER,
      icon: null,
      content: whetherInherit
        ? t('workflow.msg_reuse_noti', {
            name: id,
          })
        : t('workflow.msg_non_reuse_noti', {
            name: id,
          }),

      mask: false,
      okText: t('confirm'),
      cancelText: t('cancel'),
      style: {
        top: '35%',
      },
      onOk() {
        PubSub.publish(WORKFLOW_JOB_NODE_CHANNELS.change_inheritance, { id, data, whetherInherit });
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
