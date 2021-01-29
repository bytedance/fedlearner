import React, { FC, useRef, useState } from 'react';
import styled from 'styled-components';
import { ReactFlowProvider, useStoreState } from 'react-flow-renderer';
import { useToggle } from 'react-use';
import JobFormDrawer, { JobFormDrawerExposedRef } from './JobFormDrawer';
import WorkflowJobsFlowChart, { updateNodeStatusById } from 'components/WorkflowJobsFlowChart';
import { GlobalConfigNode, JobNode, JobNodeStatus } from 'components/WorkflowJobsFlowChart/helpers';
import GridRow from 'components/_base/GridRow';
import { Button, message, Modal, Spin } from 'antd';
import { Redirect, useHistory, useParams } from 'react-router-dom';
import { useRecoilValue } from 'recoil';
import {
  workflowConfigForm,
  workflowBasicForm,
  peerConfigInPairing,
  templateInUsing,
} from 'stores/workflow';
import { useTranslation } from 'react-i18next';
import i18n from 'i18n';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import { acceptNFillTheWorkflowConfig, initiateAWorkflow } from 'services/workflow';
import { to } from 'shared/helpers';
import { WorkflowCreateProps } from '..';
import { WorkflowAcceptPayload, WorkflowInitiatePayload } from 'typings/workflow';
import InspectPeerConfigs from './InspectPeerConfig';
import { ExclamationCircle } from 'components/IconPark';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import { stringifyWidgetSchemas } from 'shared/formSchema';
import { removePrivate } from 'shared/object';

const Container = styled.section`
  height: 100%;
`;
const Header = styled.header`
  padding: 13px 20px;
  font-size: 14px;
  line-height: 22px;
  background-color: white;
`;
const Footer = styled.footer`
  position: sticky;
  bottom: 0;
  z-index: 1000;
  padding: 15px 36px;
  background-color: white;
`;
const ChartTitle = styled.h3`
  margin-bottom: 0;
`;

const CanvasAndForm: FC<WorkflowCreateProps> = ({ isInitiate, isAccept }) => {
  const drawerRef = useRef<JobFormDrawerExposedRef>();
  const jobNodes = useStoreState((store) => store.nodes as JobNode[]);
  const history = useHistory();
  const params = useParams<{ id: string }>();
  const { t } = useTranslation();
  const [submitting, setSubmitting] = useToggle(false);
  const [drawerVisible, toggleDrawerVisible] = useToggle(false);
  const [peerCfgVisible, togglePeerCfgVisible] = useToggle(false);
  const [currNode, setCurrNode] = useState<JobNode | GlobalConfigNode>();

  const templateInUsingValue = useRecoilValue(templateInUsing);
  const workflowConfigValue = useRecoilValue(workflowConfigForm);
  const basicPayload = useRecoilValue(workflowBasicForm);
  const peerConfig = useRecoilValue(peerConfigInPairing);

  const isDisabled = { disabled: submitting };

  if (!templateInUsingValue?.config) {
    const redirectTo = isInitiate
      ? '/workflows/initiate/basic'
      : `/workflows/accept/basic/${params.id}`;
    return <Redirect to={redirectTo} />;
  }

  return (
    <ErrorBoundary>
      <Container>
        <Spin spinning={submitting} />

        <Header>
          <ChartTitle>{t('workflow.our_config')}</ChartTitle>
        </Header>

        <WorkflowJobsFlowChart
          type="config"
          jobs={templateInUsingValue.config.job_definitions}
          globalVariables={templateInUsingValue.config.variables}
          onJobClick={selectNode}
          onCanvasClick={onCanvasClick}
        />

        <JobFormDrawer
          ref={drawerRef as any}
          node={currNode!}
          visible={drawerVisible}
          toggleVisible={toggleDrawerVisible}
          onConfirm={selectNode}
          isAccept={isAccept}
          onViewPeerConfigClick={onViewPeerConfigClick}
        />

        <InspectPeerConfigs
          config={peerConfig}
          visible={peerCfgVisible}
          toggleVisible={togglePeerCfgVisible}
        />

        <Footer>
          <GridRow gap="12">
            <Button type="primary" loading={submitting} onClick={submitToCreate}>
              {t('workflow.btn_send_2_ptcpt')}
            </Button>
            <Button onClick={onPrevStepClick} {...isDisabled}>
              {t('previous_step')}
            </Button>
            <Button onClick={onCancelCreationClick} {...isDisabled}>
              {t('cancel')}
            </Button>
          </GridRow>
        </Footer>
      </Container>
    </ErrorBoundary>
  );

  function checkIfAllJobConfigCompleted() {
    const isAllCompleted = jobNodes.every((node) => {
      return node.data.status === JobNodeStatus.Success;
    });

    return isAllCompleted;
  }
  // ---------- Handlers ----------------
  function onCanvasClick() {
    drawerRef.current?.validateCurrentJobForm();
    toggleDrawerVisible(false);
  }
  async function selectNode(nextNode: JobNode | GlobalConfigNode) {
    const prevData = currNode?.data;
    if (prevData) {
      // Validate & Save current form before go another job
      await drawerRef.current?.saveCurrentValues();
      await drawerRef.current?.validateCurrentJobForm();
    }

    // Turn target node status to configuring
    updateNodeStatusById({ id: nextNode.id, status: JobNodeStatus.Processing });

    setCurrNode(nextNode);

    toggleDrawerVisible(true);
  }
  async function submitToCreate() {
    if (!checkIfAllJobConfigCompleted()) {
      return message.warn(i18n.t('workflow.msg_config_unfinished'));
    }

    toggleDrawerVisible(false);
    setSubmitting(true);

    let finalError = (null as any) as Error;

    if (isInitiate) {
      const payload = stringifyWidgetSchemas(
        removePrivate({
          config: workflowConfigValue,
          ...basicPayload,
        }) as WorkflowInitiatePayload,
      );
      const [, error] = await to(initiateAWorkflow(payload));
      finalError = error;
    }

    if (isAccept) {
      const payload = stringifyWidgetSchemas(
        removePrivate({
          config: workflowConfigValue,
          forkable: basicPayload.forkable!,
        }) as WorkflowAcceptPayload,
      );

      const [, error] = await to(acceptNFillTheWorkflowConfig(params.id, payload));
      finalError = error;
    }

    setSubmitting(false);

    if (!finalError) {
      history.push('/workflows');
    }
  }
  function onPrevStepClick() {
    history.goBack();
  }
  function onCancelCreationClick() {
    Modal.confirm({
      title: i18n.t('workflow.msg_sure_2_cancel_create'),
      icon: <ExclamationCircle />,
      zIndex: Z_INDEX_GREATER_THAN_HEADER,
      content: i18n.t('workflow.msg_effect_of_cancel_create'),
      style: {
        top: '30%',
      },
      onOk() {
        history.push('/workflows');
      },
    });
  }
  function onViewPeerConfigClick() {
    togglePeerCfgVisible(true);
  }
};

const WorkflowsCreateStepTwo: FC<WorkflowCreateProps> = (props) => {
  return (
    <ReactFlowProvider>
      <CanvasAndForm {...props} />
    </ReactFlowProvider>
  );
};

export default WorkflowsCreateStepTwo;
