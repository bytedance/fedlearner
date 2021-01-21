import React, { FC } from 'react';
import styled from 'styled-components';
import {
  isAwaitParticipantConfig,
  isCompleted,
  isStopped,
  isRunning,
  isPendingAccpet,
  isReadyToRun,
  isOperable,
  isForkable,
} from 'shared/workflow';
import { Workflow } from 'typings/workflow';
import { useTranslation } from 'react-i18next';
import { Button, message, Spin } from 'antd';
import { useHistory } from 'react-router-dom';
import { useSetRecoilState } from 'recoil';
import { workflowInEditing } from 'stores/workflow';
import { runTheWorkflow, stopTheWorkflow } from 'services/workflow';
import GridRow from 'components/_base/GridRow';
import {
  Copy,
  Sync,
  TableReport,
  SettingConfig,
  PlayCircle,
  Pause,
  Eye,
} from 'components/IconPark';
import { Icon } from 'components/IconPark/runtime';
import { useToggle } from 'react-use';

const Container = styled(GridRow)`
  margin-left: ${(props: any) => (props.type === 'link' ? '-15px !important' : 0)};
`;

type Action = 'report' | 'configure' | 'run' | 'rerun' | 'stop' | 'fork' | 'detail';
type Props = {
  workflow: Workflow;
  type?: 'link' | 'default';
  without?: Action[];
  showIcon?: boolean;
  onSuccess?: Function;
};

const icons: Record<Action, Icon> = {
  report: TableReport,
  configure: SettingConfig,
  run: PlayCircle,
  rerun: Sync,
  stop: Pause,
  detail: Eye,
  fork: Copy,
};

const WorkflowActions: FC<Props> = ({ workflow, type = 'default', without = [], onSuccess }) => {
  const { t } = useTranslation();
  const history = useHistory();
  const [loading, toggleLoading] = useToggle(false);

  const setStoreWorkflow = useSetRecoilState(workflowInEditing);

  const visible: Record<Action, boolean> = {
    configure: isPendingAccpet(workflow) && !without?.includes('configure'),
    run:
      (isReadyToRun(workflow) || isAwaitParticipantConfig(workflow)) && !without?.includes('run'),
    stop: isRunning(workflow) && !without?.includes('stop'),
    rerun: isStopped(workflow) && !without?.includes('rerun'),
    report: isCompleted(workflow) && !without?.includes('report'),
    detail: !without?.includes('detail'),
    fork: !without?.includes('fork'),
  };
  const isDisabled = !isOperable(workflow);
  const disabled = {
    configure: false,
    run: isDisabled,
    stop: isDisabled,
    rerun: isDisabled,
    fork: !isForkable(workflow),
  };
  const isDefaultType = type === 'default';

  return (
    <Spin spinning={loading} size="small">
      <Container {...{ type }} gap={isDefaultType ? 8 : 0}>
        {visible.report && (
          <Button
            size="small"
            type={type}
            {...withIcon('report')}
            onClick={onAcceptClick}
            disabled={disabled.configure}
          >
            {t('workflow.action_show_report')}
          </Button>
        )}
        {visible.configure && (
          <Button size="small" type={type} {...withIcon('configure')} onClick={onAcceptClick}>
            {t('workflow.action_configure')}
          </Button>
        )}
        {visible.run && (
          <Button
            size="small"
            type={type}
            {...withIcon('run')}
            onClick={onRunClick}
            disabled={disabled.run}
          >
            {t('workflow.action_run')}
          </Button>
        )}
        {visible.stop && (
          <Button
            size="small"
            type={type}
            {...withIcon('stop')}
            onClick={onStopClick}
            disabled={disabled.stop}
          >
            {t('workflow.action_stop_running')}
          </Button>
        )}
        {visible.rerun && (
          <Button
            size="small"
            type={type}
            {...withIcon('rerun')}
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
            {...withIcon('fork')}
            onClick={onForkClick}
            disabled={disabled.fork}
          >
            {t('workflow.action_fork')}
          </Button>
        )}
        {visible.detail && (
          <Button size="small" type={type} {...withIcon('detail')} onClick={onViewDetailClick}>
            {t('workflow.action_detail')}
          </Button>
        )}
      </Container>
    </Spin>
  );

  function withIcon(action: Action) {
    if (!isDefaultType) return {};

    const Ico = icons[action];
    return {
      icon: <Ico />,
    };
  }
  function onAcceptClick() {
    setStoreWorkflow(workflow);
    history.push(`/workflows/accept/basic/${workflow.id}`);
  }
  function onViewDetailClick() {
    history.push(`/workflows/${workflow.id}`);
  }
  function onForkClick() {
    // TODO: fork workflow
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
};

export default WorkflowActions;
