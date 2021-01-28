import React, { FC, useRef, useState } from 'react';
import styled from 'styled-components';
import { ReactFlowProvider, useStoreState } from 'react-flow-renderer';
import { useToggle } from 'react-use';
import JobFormDrawer, { JobFormDrawerExposedRef } from './JobFormDrawer';
import WorkflowJobsFlowChart, { updateNodeStatusById } from 'components/WorkflowJobsFlowChart';
import { JobNode, JobNodeData, JobNodeStatus } from 'components/WorkflowJobsFlowChart/helpers';
import GridRow from 'components/_base/GridRow';
import { Button, message, Modal, Spin } from 'antd';
import { Redirect, useHistory, useParams } from 'react-router-dom';
import { useRecoilValue } from 'recoil';
import {
  workflowJobsConfigForm,
  workflowGetters,
  workflowBasicForm,
  peerConfigInPairing,
} from 'stores/workflow';
import { useTranslation } from 'react-i18next';
import i18n from 'i18n';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import { acceptNFillTheWorkflowConfig, initiateAWorkflow } from 'services/workflow';
import { to } from 'shared/helpers';
import { WorkflowCreateProps } from '..';
import { WorkflowInitiatePayload } from 'typings/workflow';
import InspectPeerConfigs from './InspectPeerConfig';
import { ExclamationCircle } from 'components/IconPark';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';

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
  const [data, setData] = useState<JobNodeData>();

  const { currentWorkflowTpl } = useRecoilValue(workflowGetters);
  const jobsConfigPayload = useRecoilValue(workflowJobsConfigForm);
  const basicPayload = useRecoilValue(workflowBasicForm);
  const peerConfig = useRecoilValue(peerConfigInPairing);

  const isDisabled = { disabled: submitting };

  if (currentWorkflowTpl === null) {
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
          jobs={currentWorkflowTpl.config.job_definitions}
          globalVariables={currentWorkflowTpl.config.variables}
          onJobClick={selectJob}
          onCanvasClick={onCanvasClick}
        />

        <JobFormDrawer
          ref={drawerRef as any}
          data={data}
          visible={drawerVisible}
          toggleVisible={toggleDrawerVisible}
          onConfirm={selectJob}
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
  async function selectJob(jobNode: JobNode) {
    // Turn node status to configuring
    updateNodeStatusById({ id: jobNode.id, status: JobNodeStatus.Processing });

    if (jobNode.data.status !== JobNodeStatus.Processing) {
      await drawerRef.current?.validateCurrentJobForm();
    }
    if (data) {
      drawerRef.current?.saveCurrentValues();
    }
    setData(jobNode.data);

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
      const payload = { config: jobsConfigPayload, ...basicPayload };
      const [_, error] = await to(initiateAWorkflow(payload as WorkflowInitiatePayload));
      finalError = error;
    }

    if (isAccept) {
      const [_, error] = await to(
        acceptNFillTheWorkflowConfig(params.id, {
          config: jobsConfigPayload,
          forkable: basicPayload.forkable!,
        }),
      );
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
