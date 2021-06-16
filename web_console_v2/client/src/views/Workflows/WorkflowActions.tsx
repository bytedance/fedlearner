import React, { FC } from 'react';
import styled, { createGlobalStyle } from 'styled-components';
import {
  isAwaitParticipantConfig,
  isCompleted,
  isStopped,
  isRunning,
  isFailed,
  isPendingAccpet,
  isReadyToRun,
  isOperable,
  isForkable,
  isInvalid,
} from 'shared/workflow';
import { Workflow } from 'typings/workflow';
import { useTranslation } from 'react-i18next';
import { Button, message, Spin, Popconfirm } from 'antd';
import { useHistory } from 'react-router-dom';
import {
  getPeerWorkflowsConfig,
  runTheWorkflow,
  stopTheWorkflow,
  invalidTheWorkflow,
} from 'services/workflow';
import WorkflowAccessControl from './WorkflowAccessControl';
import GridRow from 'components/_base/GridRow';
import { Copy, Sync, TableReport, Tool, PlayCircle, Pause, Edit } from 'components/IconPark';
import { useToggle } from 'react-use';
import { to } from 'shared/helpers';
import { ControlOutlined } from '@ant-design/icons';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';

const Container = styled(GridRow)`
  width: fit-content;
  margin-left: ${(props: any) => (props.type === 'link' ? '-10px !important' : 0)};
`;
const SpinnerWrapperStyle = createGlobalStyle`
  .spinnerWrapper {
    width: fit-content;
  }
`;

type Action =
  | 'edit'
  | 'report'
  | 'configure'
  | 'run'
  | 'rerun'
  | 'stop'
  | 'fork'
  | 'invalid'
  | 'accessCtrl';

type Props = {
  workflow: Workflow;
  type?: 'link' | 'default';
  without?: Action[];
  showIcon?: boolean;
  onSuccess?: Function;
};

const icons: Partial<Record<Action, any>> = {
  report: TableReport,
  configure: Tool,
  run: PlayCircle,
  rerun: Sync,
  stop: Pause,
  fork: Copy,
  edit: Edit,
  accessCtrl: ControlOutlined,
};

const WorkflowActions: FC<Props> = ({ workflow, type = 'default', without = [], onSuccess }) => {
  const { t } = useTranslation();
  const history = useHistory();
  const [loading, toggleLoading] = useToggle(false);

  const visible: Partial<Record<Action, boolean>> = {
    configure: isPendingAccpet(workflow) && !without?.includes('configure'),
    run:
      (isReadyToRun(workflow) || isAwaitParticipantConfig(workflow)) && !without?.includes('run'),
    stop:
      (isFailed(workflow) || isRunning(workflow) || isCompleted(workflow)) &&
      !without?.includes('stop'),
    rerun: isStopped(workflow) && !without?.includes('rerun'),
    report: isCompleted(workflow) && !without?.includes('report'),
    fork: !without?.includes('fork'),
    accessCtrl: !without?.includes('accessCtrl'),
    invalid: !without?.includes('fork') && !isInvalid(workflow),
    edit: !without?.includes('edit'),
  };

  const isDisabled = !isOperable(workflow);

  const disabled = {
    configure: false,
    run: isDisabled,
    stop: isDisabled,
    rerun: isDisabled,
    fork: !isForkable(workflow),
    invalid: false,
    report: true,
    accessCtrl: false,
    edit: isRunning(workflow),
  };

  const isDefaultType = type === 'default';

  return (
    <ErrorBoundary>
      <Spin spinning={loading} size="small" wrapperClassName="spinnerWrapper">
        <SpinnerWrapperStyle />
        <Container {...{ type }} gap={isDefaultType ? 8 : 0}>
          {visible.edit && (
            <Button
              size="small"
              type={type}
              icon={withIcon('edit')}
              disabled={disabled.edit}
              onClick={onEditClick}
            >
              {t('workflow.action_edit')}
            </Button>
          )}
          {visible.report && (
            // TODO: workflow model report
            <Button size="small" type={type} icon={withIcon('report')} disabled={disabled.report}>
              {t('workflow.action_show_report')}
            </Button>
          )}
          {visible.configure && (
            <Button size="small" type={type} icon={withIcon('configure')} onClick={onAcceptClick}>
              {t('workflow.action_configure')}
            </Button>
          )}
          {visible.run && (
            <Button
              size="small"
              type={type}
              icon={withIcon('run')}
              onClick={onRunClick}
              disabled={disabled.run}
            >
              {t('workflow.action_run')}
            </Button>
          )}
          {visible.stop && (
            <Popconfirm title={t('workflow.msg_sure_to_stop')} onConfirm={onStopClick}>
              <Button size="small" type={type} icon={withIcon('stop')} disabled={disabled.stop}>
                {t('workflow.action_stop_running')}
              </Button>
            </Popconfirm>
          )}
          {visible.rerun && (
            <Button
              size="small"
              type={type}
              icon={withIcon('rerun')}
              onClick={onRunClick}
              disabled={disabled.rerun}
            >
              {t('workflow.action_re_run')}
            </Button>
          )}
          {visible.fork && (
            <Button
              size="small"
              type={type}
              icon={withIcon('fork')}
              onClick={onForkClick}
              disabled={disabled.fork}
            >
              {t('workflow.action_fork')}
            </Button>
          )}
          {visible.invalid && (
            <Button
              size="small"
              type={type}
              onClick={onInvalidClick}
              danger
              disabled={disabled.invalid}
            >
              {t('workflow.action_invalid')}
            </Button>
          )}
          {visible.accessCtrl && (
            <WorkflowAccessControl
              icon={withIcon('accessCtrl')}
              size="small"
              type={type}
              workflow={workflow}
              disabled={disabled.accessCtrl}
            />
          )}
        </Container>
      </Spin>
    </ErrorBoundary>
  );

  function withIcon(action: Action) {
    if (!isDefaultType) return undefined;

    const Ico = icons[action];

    if (!Ico) return undefined;

    return <Ico />;
  }
  function onEditClick() {
    history.push(`/workflows/edit/basic/${workflow.id}`);
  }
  function onAcceptClick() {
    history.push(`/workflows/accept/basic/${workflow.id}`);
  }
  async function onForkClick() {
    toggleLoading(true);
    const [res, error] = await to(getPeerWorkflowsConfig(workflow.id));
    toggleLoading(false);

    if (error) {
      return message.error(t('workflow.msg_get_peer_cfg_failed') + error.message);
    }

    const anyPeerWorkflow = Object.values(res.data).find((item) => !!item.uuid)!;
    if (!anyPeerWorkflow.forkable) {
      message.warning(t('workflow.msg_unforkable'));
      return;
    }

    history.push(`/workflows/fork/basic/${workflow.id}`);
  }
  async function onRunClick() {
    toggleLoading(true);
    try {
      await runTheWorkflow(workflow.id);
      onSuccess && onSuccess(workflow);
    } catch (error) {
      message.error(error.message);
    }
    toggleLoading(false);
  }
  async function onStopClick() {
    toggleLoading(true);
    try {
      await stopTheWorkflow(workflow.id);
      onSuccess && onSuccess(workflow);
    } catch (error) {
      message.error(error.message);
    }
    toggleLoading(false);
  }
  async function onInvalidClick() {
    toggleLoading(true);
    try {
      await invalidTheWorkflow(workflow.id);
      onSuccess && onSuccess(workflow);
    } catch (error) {
      message.error(error.message);
    }
    toggleLoading(false);
  }
};

export default WorkflowActions;
