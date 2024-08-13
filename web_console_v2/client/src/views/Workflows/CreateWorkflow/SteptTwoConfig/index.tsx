import React, { FC, useEffect, useRef, useState } from 'react';
import styled from './index.module.less';
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
import { Button, Message, Spin } from '@arco-design/web-react';
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
import ErrorBoundary from 'components/ErrorBoundary';
import { acceptNFillTheWorkflowConfig, initiateAWorkflow } from 'services/workflow';
import { to } from 'shared/helpers';
import { WorkflowCreateProps } from '..';
import { WorkflowAcceptPayload, WorkflowInitiatePayload } from 'typings/workflow';
import InspectPeerConfigs from '../../InspectPeerConfig';
import Modal from 'components/Modal';
import { stringifyComplexDictField } from 'shared/formSchema';
import { removePrivate } from 'shared/object';
import { cloneDeep } from 'lodash-es';
import { useSubscribe } from 'hooks';
import { WORKFLOW_JOB_NODE_CHANNELS } from 'components/WorkflowJobsCanvas/JobNodes/shared';
import { CreateJobFlag } from 'typings/job';
import { hydrate } from 'views/Workflows/shared';
import { Variable } from 'typings/variable';

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

  useSubscribe(WORKFLOW_JOB_NODE_CHANNELS.disable_job, onNodeDisabledChange, [chartRef.current]);

  const isDisabled = { disabled: submitting };

  if (!template?.config) {
    const redirectTo = isInitiate
      ? '/workflow-center/workflows/initiate/basic'
      : `/workflow-center/workflows/accept/basic/${params.id}`;
    return <Redirect to={redirectTo} />;
  }

  const currNodeValues =
    currNode?.type === 'global'
      ? configValue.variables
      : configValue.job_definitions.find((item) => item.name === currNode?.id)?.variables;

  return (
    <ErrorBoundary>
      <section className={styled.container}>
        <Spin loading={submitting}>
          <header className={styled.chart_header}>
            <h3 className={styled.chart_title}>{t('workflow.our_config')}</h3>
          </header>
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

        <footer className={styled.footer}>
          <GridRow gap="12">
            <Button type="primary" loading={submitting} onClick={submitToCreate}>
              {template.is_local ? '创建单侧工作流' : t('workflow.btn_send_2_ptcpt')}
            </Button>
            <Button onClick={onPrevStepClick} {...isDisabled}>
              {t('previous_step')}
            </Button>
            <Button onClick={onCancelCreationClick} {...isDisabled}>
              {t('cancel')}
            </Button>
          </GridRow>
        </footer>
      </section>
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
    const nextValue = cloneDeep(configValue);

    if (currNode?.type === 'global') {
      // Hydrate values to workflow global variables
      nextValue.variables = hydrate(nextValue.variables, values) as Variable[];
    }

    if (currNode?.type === 'config') {
      // Hydrate values to target job
      const targetJob = nextValue.job_definitions.find((job) => job.name === currNode.id);
      if (targetJob) {
        targetJob.variables = hydrate(targetJob.variables, values) as Variable[];
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
      return Message.warning(i18n.t('workflow.msg_config_unfinished'));
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

      payload.template_id = template.id;

      payload.template_revision_id = template.revision_id;

      const [, error] = await to(initiateAWorkflow(payload, payload.project_id));
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

      payload.template_id = template.id;

      const [, error] = await to(
        acceptNFillTheWorkflowConfig(params.id, payload, basicPayload.project_id!),
      );
      resError = error;
    }

    setSubmitting(false);

    if (!resError) {
      history.push('/workflow-center/workflows');
    } else {
      Message.error(resError.message);
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
      content: i18n.t('workflow.msg_effect_of_cancel_create'),
      onOk() {
        history.push('/workflow-center/workflows');
      },
    });
  }
  function onViewPeerConfigClick() {
    togglePeerCfgVisible(true);
  }
};

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
