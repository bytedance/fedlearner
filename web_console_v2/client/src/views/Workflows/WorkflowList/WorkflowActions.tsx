import React, { FC } from 'react';
import styled from 'styled-components';
import { isStopped, isRunning, isPendingAccpet, isReadyToRun } from 'shared/workflow';
import { Workflow } from 'typings/workflow';
import { useTranslation } from 'react-i18next';
import { Button } from 'antd';
import { useHistory } from 'react-router-dom';
import { useSetRecoilState } from 'recoil';
import { workflowInEditing } from 'stores/workflow';

const Container = styled.div`
  margin-left: -7px;
`;

const WorkflowActions: FC<{ workflow: Workflow }> = ({ workflow }) => {
  const { t } = useTranslation();
  const history = useHistory();
  const setStoreWorkflow = useSetRecoilState(workflowInEditing);

  return (
    <Container>
      {isPendingAccpet(workflow) && (
        <Button size="small" type="link" onClick={onAcceptClick}>
          {t('workflow.action_configure')}
        </Button>
      )}
      {isReadyToRun(workflow) && (
        <Button size="small" type="link">
          {t('workflow.action_run')}
        </Button>
      )}
      {isRunning(workflow) && (
        <Button size="small" type="link">
          {t('workflow.action_stop_running')}
        </Button>
      )}
      {isStopped(workflow) && (
        <Button size="small" type="link">
          {t('workflow.action_re_run')}
        </Button>
      )}
      <Button size="small" type="link">
        {t('workflow.action_duplicate')}
      </Button>
      <Button size="small" type="link">
        {t('workflow.action_detail')}
      </Button>
    </Container>
  );

  function onAcceptClick() {
    setStoreWorkflow(workflow);
    console.log('🚀 ~ file: WorkflowActions.tsx ~ line 53 ~ onAcceptClick ~ workflow', workflow);
    history.push(`/workflows/accept/basic/${workflow.id}`);
  }
};

export default WorkflowActions;
