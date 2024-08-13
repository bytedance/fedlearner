/* istanbul ignore file */

import { ChartNodeStatus, GlobalNodeRawData, NodeData } from '../types';
import pendingIcon from 'assets/icons/workflow-pending.svg';
import completetdIcon from 'assets/icons/workflow-completed.svg';
import warningIcon from 'assets/icons/workflow-warning.svg';
import errorIcon from 'assets/icons/workflow-error.svg';
import i18n from 'i18n';
import { NodeComponentProps } from 'react-flow-renderer';

export const statusIcons: Record<ChartNodeStatus, string> = {
  [ChartNodeStatus.Pending]: '',
  [ChartNodeStatus.Processing]: pendingIcon,
  [ChartNodeStatus.Validating]: pendingIcon,
  [ChartNodeStatus.Success]: completetdIcon,
  [ChartNodeStatus.Warning]: warningIcon,
  [ChartNodeStatus.Error]: errorIcon,
};

export const configStatusText: Record<ChartNodeStatus, string> = {
  [ChartNodeStatus.Pending]: i18n.t('workflow.job_node_pending'),
  [ChartNodeStatus.Validating]: i18n.t('workflow.job_node_validating'),
  [ChartNodeStatus.Processing]: i18n.t('workflow.job_node_configuring'),
  [ChartNodeStatus.Success]: i18n.t('workflow.job_node_config_completed'),
  [ChartNodeStatus.Warning]: i18n.t('workflow.job_node_unfinished'),
  [ChartNodeStatus.Error]: i18n.t('workflow.job_node_invalid'),
};

export const executionStatusText: Partial<Record<ChartNodeStatus, string>> = {
  [ChartNodeStatus.Pending]: i18n.t('workflow.job_node_waiting'),
  [ChartNodeStatus.Processing]: i18n.t('workflow.job_node_running'),
  [ChartNodeStatus.Success]: i18n.t('workflow.job_node_success'),
  [ChartNodeStatus.Warning]: i18n.t('workflow.job_node_failed'),
  [ChartNodeStatus.Error]: i18n.t('workflow.job_node_stop_running'),
};

export interface JobNodeProps extends NodeComponentProps {
  data: NodeData;
}

export interface GlobalNodeProps extends NodeComponentProps {
  data: NodeData<GlobalNodeRawData>;
}

export const WORKFLOW_JOB_NODE_CHANNELS = {
  change_inheritance: 'job_node.change_inheritance',
  disable_job: 'job_node.disable_job',
  click_add_job: 'job_node.click_add_job',
};
