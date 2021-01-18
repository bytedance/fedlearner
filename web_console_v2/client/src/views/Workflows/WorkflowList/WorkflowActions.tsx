import React, { FC } from 'react';
import styled from 'styled-components';
import {
  isStopped,
  isRunning,
  isPendingAccpet,
  isReadyToRun,
  isOperable,
  isAwaitParticipantConfig,
} from 'shared/workflow';
import { Workflow } from 'typings/workflow';
import { useTranslation } from 'react-i18next';
import { Button } from 'antd';
import { useHistory } from 'react-router-dom';
import { useSetRecoilState } from 'recoil';
import { workflowInEditing } from 'stores/workflow';
import { runTheWorkflow, stopTheWorkflow } from 'services/workflow';

const Container = styled.div`
  margin-left: -7px;
`;

const WorkflowActions: FC<{ workflow: Workflow }> = ({ workflow }) => {
  const { t } = useTranslation();
  const history = useHistory();
  const setStoreWorkflow = useSetRecoilState(workflowInEditing);

  const visible = {
    configure: isPendingAccpet(workflow),
    run: isReadyToRun(workflow) || isAwaitParticipantConfig(workflow),
    stop: isRunning(workflow),
    rerun: isStopped(workflow),
  };
  const isDisabled = !isOperable(workflow);
  const disabled = {
    configure: isDisabled,
    run: isDisabled,
    stop: isDisabled,
    rerun: isDisabled,
    fork: isDisabled,
  };

  return (
    <Container>
      {visible.configure && (
        <Button size="small" type="link" onClick={onAcceptClick} disabled={disabled.configure}>
          {t('workflow.action_configure')}
        </Button>
      )}
      {visible.run && (
        <Button size="small" type="link" onClick={onRunClick} disabled={disabled.run}>
          {t('workflow.action_run')}
        </Button>
      )}
      {visible.stop && (
        <Button size="small" type="link" onClick={onStopClick} disabled={disabled.stop}>
          {t('workflow.action_stop_running')}
        </Button>
      )}
      {visible.rerun && (
        <Button size="small" type="link" onClick={onRunClick} disabled={disabled.rerun}>
          {t('workflow.action_re_run')}
        </Button>
      )}
      <Button size="small" type="link" onClick={onForkClick} disabled={disabled.fork}>
        {t('workflow.action_fork')}
      </Button>
      <Button size="small" type="link" onClick={onViewDetailClick}>
        {t('workflow.action_detail')}
      </Button>
    </Container>
  );

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
    await runTheWorkflow(workflow.id);
  }
  async function onStopClick() {
    await stopTheWorkflow(workflow.id);
  }
};

export default WorkflowActions;
