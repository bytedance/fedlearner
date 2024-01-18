import React, { FC, useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import {
  ReactFlowProvider,
  useStoreState,
  useStoreActions,
  ReactFlowState,
} from 'react-flow-renderer';
import { useToggle } from 'react-use';
import JobFormDrawer, { JobFormDrawerExposedRef } from '../../JobFormDrawer';
import WorkflowJobsCanvas, { ChartExposedRef } from 'components/WorkflowJobsCanvas';
import {
  ChartNode,
  ChartNodes,
  ChartNodeStatus,
  NodeData,
} from 'components/WorkflowJobsCanvas/types';
import GridRow from 'components/_base/GridRow';
import { Button, message, Modal, Spin } from 'antd';
import { Redirect, useHistory, useParams } from 'react-router-dom';
import { useRecoilValue, useRecoilState } from 'recoil';
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
import { Variable } from 'typings/variable';
import InspectPeerConfigs from '../../InspectPeerConfig';
import { ExclamationCircle } from 'components/IconPark';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import { stringifyComplexDictField } from 'shared/formSchema';
import { removePrivate } from 'shared/object';
import { cloneDeep, Dictionary } from 'lodash';
import { useSubscribe } from 'hooks';
import { WORKFLOW_JOB_NODE_CHANNELS } from 'components/WorkflowJobsCanvas/JobNodes/shared';
import { CreateJobFlag } from 'typings/job';

const Container = styled.section`
  height: 100%;
`;
const ChartHeader = styled.header`
  height: 48px;
  padding: 13px 20px;
  font-size: 14px;
  line-height: 22px;
  background-color: white;
`;
const Footer = styled.footer`
  position: sticky;
  bottom: 0;
  z-index: 5; // just above react-flow' z-index
  padding: 15px 36px;
  background-color: white;
`;
const ChartTitle = styled.h3`
  margin-bottom: 0;
`;

const CanvasAndForm: FC<WorkflowCreateProps> = ({ isInitiate, isAccept }) => {
  const history = useHistory();
  const params = useParams<{ id: string }>();
  const { t } = useTranslation();
  const drawerRef = useRef<JobFormDrawerExposedRef>();
  const chartRef = useRef<ChartExposedRef>();
  const [submitting, setSubmitting] = useToggle(false);
  const [drawerVisible, toggleDrawerVisible] = useToggle(false);
  const [peerCfgVisible, togglePeerCfgVisible] = useToggle(false);
  const [currNode, setCurrNode] = useState<ChartNode>();
  /**
   * Here we could use react-flow hooks is because we
   * wrap CanvasAndForm with ReactFlowProvider in lines at the bottom
   */
  const jobNodes = useStoreState((store: ReactFlowState) => store.nodes as ChartNodes);
  const setSelectedElements = useStoreActions((actions) => actions.setSelectedElements);

  const template = useRecoilValue(templateInUsing);
  const [configValue, setConfigValue] = useRecoilState(workflowConfigForm);
  const basicPayload = useRecoilValue(workflowBasicForm);
  const peerConfig = useRecoilValue(peerConfigInPairing);

  /**
   * Open drawer if have global config node
   */
  useEffect(() => {
    if (jobNodes[0] && jobNodes[0].type === 'global') {
      selectNode(jobNodes[0]);
    }
    // 1. DO NOT INCLUDE selectNode as deps here, every render selectNode is freshly new
    // 2. DO NOT INCLUDE jobNodes as direct dep too, since selectNode has side-effect to node's data (modify status underneath)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobNodes[0]?.type]);

  useSubscribe(WORKFLOW_JOB_NODE_CHANNELS.disable_job, onNodeDisabledChange);

  const isDisabled = { disabled: submitting };

  if (!template?.config) {
    const redirectTo = isInitiate
      ? '/workflows/initiate/basic'
      : `/workflows/accept/basic/${params.id}`;
    return <Redirect to={redirectTo} />;
  }

  const currNodeValues =
    currNode?.type === 'global'
      ? configValue.variables
      : configValue.job_definitions.find((item) => item.name === currNode?.id)?.variables;

  return (
    <ErrorBoundary>
      <Container>
        <Spin spinning={submitting}>
          <ChartHeader>
            <ChartTitle>{t('workflow.our_config')}</ChartTitle>
          </ChartHeader>
        </Spin>

        <WorkflowJobsCanvas
          ref={chartRef as any}
          nodeType="config"
          workflowConfig={configValue}
          onJobClick={selectNode}
          onCanvasClick={onCanvasClick}
        />

        <JobFormDrawer
          ref={drawerRef as any}
          visible={drawerVisible}
          toggleVisible={toggleDrawerVisible}
          showPeerConfigButton={isAccept && Boolean(peerConfig)}
          currentIdx={currNode?.data.index}
          nodesCount={jobNodes.length}
          jobDefinition={currNode?.data.raw}
          initialValues={currNodeValues}
          onGoNextJob={onGoNextJob}
          onCloseDrawer={onCloseDrawer}
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

  // --------- Methods ---------------
  function checkIfAllJobConfigCompleted() {
    const isAllCompleted = jobNodes.every((node: ChartNode) => {
      // Whether a node has Success status or it's been disabled
      // we recognize it as complete!
      return node.data.status === ChartNodeStatus.Success || node.data.disabled;
    });

    return isAllCompleted;
  }

  async function saveCurrentValues() {
    const values = await drawerRef.current?.getFormValues();

    let nextValue = cloneDeep(configValue);

    if (currNode?.type === 'global') {
      // Hydrate values to workflow global variables
      nextValue.variables = _hydrate(nextValue.variables, values);
    }

    if (currNode?.type === 'config') {
      // Hydrate values to target job
      const targetJob = nextValue.job_definitions.find((job) => job.name === currNode.id);
      if (targetJob) {
        targetJob.variables = _hydrate(targetJob.variables, values);
      }
    }

    setConfigValue(nextValue);
  }
  async function validateCurrentValues() {
    if (!currNode) return;
    const isValid = await drawerRef.current?.validateCurrentForm();
    chartRef.current?.updateNodeStatusById({
      id: currNode.id,
      status: isValid ? ChartNodeStatus.Success : ChartNodeStatus.Warning,
    });
  }
  /** 🚀 Initiate create request */
  async function submitToCreate() {
    if (!checkIfAllJobConfigCompleted()) {
      return message.warn(i18n.t('workflow.msg_config_unfinished'));
    }

    toggleDrawerVisible(false);
    setSubmitting(true);

    let resError: Error | null = null;

    if (isInitiate) {
      const payload = stringifyComplexDictField(
        removePrivate({
          config: configValue,
          ...basicPayload,
        }) as WorkflowInitiatePayload,
      );

      payload.name = payload.name.trim();

      payload.create_job_flags = _mapJobFlags(chartRef.current?.nodes);

      const [, error] = await to(initiateAWorkflow(payload));
      resError = error;
    }

    if (isAccept) {
      const payload = stringifyComplexDictField(
        removePrivate({
          config: configValue,
          forkable: basicPayload.forkable!,
        }) as WorkflowAcceptPayload,
      );

      payload.create_job_flags = _mapJobFlags(chartRef.current?.nodes);

      const [, error] = await to(acceptNFillTheWorkflowConfig(params.id, payload));
      resError = error;
    }

    setSubmitting(false);

    if (!resError) {
      history.push('/workflows');
    } else {
      message.error(resError.message);
    }
  }
  async function selectNode(nextNode: ChartNode) {
    const prevNode = currNode;
    if (currNode && prevNode) {
      // Validate & Save current form before go another job
      await validateCurrentValues();
      await saveCurrentValues();
    }

    // Turn target node status to configuring
    chartRef.current?.updateNodeStatusById({ id: nextNode.id, status: ChartNodeStatus.Processing });

    setCurrNode(nextNode);
    setSelectedElements([nextNode]);

    toggleDrawerVisible(true);
  }

  // ---------- Handlers ----------------
  async function onCanvasClick() {
    await validateCurrentValues();
    saveCurrentValues();
    toggleDrawerVisible(false);
  }
  async function onCloseDrawer() {
    await validateCurrentValues();
    saveCurrentValues();
    setSelectedElements([]);
  }
  function onGoNextJob() {
    if (!currNode) return;

    const nextNodeToSelect = jobNodes.find(
      (node: ChartNode) => node.data.index === currNode.data.index + 1,
    );
    nextNodeToSelect && selectNode(nextNodeToSelect);
  }
  function onPrevStepClick() {
    history.goBack();
  }

  function onNodeDisabledChange(
    _: string,
    { data, ...payload }: { id: string; data: NodeData; disabled: boolean },
  ) {
    chartRef.current?.updateNodeDisabledById(payload);
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

/**
 * @param variableShells Variable defintions without any user input value
 * @param formValues User inputs
 */
function _hydrate(variableShells: Variable[], formValues?: Dictionary<any>): Variable[] {
  if (!formValues) return [];

  return variableShells.map((item) => {
    return {
      ...item,
      value: formValues[item.name],
    };
  });
}

function _mapJobFlags(nodes?: ChartNodes) {
  if (!nodes) return [];

  return nodes
    .filter((node) => node.type !== 'global')
    .map((node) => {
      if (node.data.disabled) {
        return CreateJobFlag.DISABLED;
      }

      return CreateJobFlag.NEW;
    });
}

const WorkflowsCreateStepTwo: FC<WorkflowCreateProps> = (props) => {
  return (
    <ReactFlowProvider>
      <CanvasAndForm {...props} />
    </ReactFlowProvider>
  );
};

export default WorkflowsCreateStepTwo;
