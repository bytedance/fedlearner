import React, { FC, useMemo, useRef, useState } from 'react';
import styled from './index.module.less';
import { ReactFlowProvider } from 'react-flow-renderer';
import { useToggle } from 'react-use';
import JobFormDrawer, { JobFormDrawerExposedRef } from '../../JobFormDrawer';
import WorkflowJobsCanvas, { ChartExposedRef } from 'components/WorkflowJobsCanvas';
import {
  ChartNode,
  ChartNodeStatus,
  JobNodeRawData,
  NodeData,
} from 'components/WorkflowJobsCanvas/types';
import GridRow from 'components/_base/GridRow';
import { Button, Message, Spin, Grid } from '@arco-design/web-react';
import { Redirect, useHistory, useParams } from 'react-router-dom';
import { useRecoilValue, useRecoilState } from 'recoil';
import {
  workflowConfigForm,
  workflowBasicForm,
  peerConfigInPairing,
  workflowInEditing,
  templateInUsing,
} from 'stores/workflow';
import { useTranslation } from 'react-i18next';
import i18n from 'i18n';
import ErrorBoundary from 'components/ErrorBoundary';
import { patchWorkflow, patchPeerWorkflow } from 'services/workflow';
import { to } from 'shared/helpers';
import { WorkflowAcceptPayload } from 'typings/workflow';
import InspectPeerConfigs from '../../InspectPeerConfig';
import Modal from 'components/Modal';
import { stringifyComplexDictField } from 'shared/formSchema';
import { cloneDeep } from 'lodash-es';
import { useSubscribe } from 'hooks';
import { WORKFLOW_JOB_NODE_CHANNELS } from 'components/WorkflowJobsCanvas/JobNodes/shared';
import { CreateJobFlag } from 'typings/job';
import { hydrate } from 'views/Workflows/shared';
import LocalWorkflowNote from 'views/Workflows/LocalWorkflowNote';
import { Side } from 'typings/app';
import { Variable } from 'typings/variable';

const Row = Grid.Row;

const WorkflowEditStepTwoConfig: FC = () => {
  const history = useHistory();
  const params = useParams<{ id: string }>();
  const { t } = useTranslation();
  const drawerRef = useRef<JobFormDrawerExposedRef>();
  const selfConfigChartRef = useRef<ChartExposedRef>();
  const peerConfigChartRef = useRef<ChartExposedRef>();
  const [side, setSide] = useState<Side>('self');
  const [submitting, setSubmitting] = useToggle(false);
  const [drawerVisible, toggleDrawerVisible] = useToggle(false);
  const [peerCfgVisible, togglePeerCfgVisible] = useToggle(false);
  const [currNode, setCurrNode] = useState<ChartNode>();
  const isChangedPeerConfigValue = useRef(false);

  const [workflow, setWorkflow] = useRecoilState(workflowInEditing);
  const [configValue, setConfigValue] = useRecoilState(workflowConfigForm);
  const [peerConfigValue, setPeerConfigValue] = useRecoilState(peerConfigInPairing);
  const basicPayload = useRecoilValue(workflowBasicForm);
  const template = useRecoilValue(templateInUsing);

  useSubscribe(WORKFLOW_JOB_NODE_CHANNELS.disable_job, onNodeDisabledChange);

  const targetConfigValueState = getConfigValueState(side);
  const targetChartRef = getChartRef(side);

  const processedConfig = useMemo(() => {
    // When using original template, we have the flags tell jobs' reuse/disable status
    // mark them on the job raw data
    if (workflow?.create_job_flags && basicPayload._keepUsingOriginalTemplate) {
      const clonedConfig = cloneDeep(configValue);
      _markJobFlags(clonedConfig.job_definitions, workflow.create_job_flags);
      return clonedConfig;
    }
    return configValue;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflow?.create_job_flags]);

  if (!workflow) {
    const redirectTo = `/workflow-center/workflows/edit/basic/${params.id}`;
    return <Redirect to={redirectTo} />;
  }

  const currNodeVars =
    currNode?.type === 'global'
      ? targetConfigValueState[0].variables
      : targetConfigValueState[0].job_definitions.find((item) => item.name === currNode?.id)
          ?.variables;

  const isDisabled = { disabled: submitting };
  const isCurrNodeReused = currNode && (currNode.data.raw as JobNodeRawData).reused;
  const isLocalWorkflow = workflow.is_local;

  return (
    <ErrorBoundary>
      <section className={styled.container}>
        <div className={styled.chart_container}>
          <Spin loading={submitting}>
            <Row className={styled.chart_header} justify="space-between" align="center">
              <h3 className={styled.chart_title}>{t('workflow.our_config')}</h3>
              {isLocalWorkflow && <LocalWorkflowNote />}
            </Row>
          </Spin>
          <ReactFlowProvider>
            <WorkflowJobsCanvas
              ref={selfConfigChartRef as any}
              nodeType="edit"
              nodeInitialStatus={
                basicPayload._keepUsingOriginalTemplate
                  ? ChartNodeStatus.Success
                  : ChartNodeStatus.Pending
              }
              workflowConfig={processedConfig}
              onJobClick={(node) => selectNode(node, 'self')}
              onCanvasClick={onCanvasClick}
            />
          </ReactFlowProvider>
        </div>

        {!workflow.is_local && Boolean(peerConfigValue) && (
          <div className={styled.chart_container}>
            <Spin loading={submitting}>
              <Row className={styled.chart_header} justify="space-between" align="center">
                <h3 className={styled.chart_header}>{t('workflow.peer_config')}</h3>
              </Row>
            </Spin>

            <ReactFlowProvider>
              <WorkflowJobsCanvas
                ref={peerConfigChartRef}
                side="peer"
                nodeType="edit"
                nodeInitialStatus={
                  basicPayload._keepUsingOriginalTemplate
                    ? ChartNodeStatus.Success
                    : ChartNodeStatus.Pending
                }
                workflowConfig={peerConfigValue as any}
                onCanvasClick={onCanvasClick}
                onJobClick={(node) => selectNode(node, 'peer')}
              />
            </ReactFlowProvider>
          </div>
        )}
      </section>

      <JobFormDrawer
        ref={drawerRef as any}
        visible={drawerVisible}
        isPeerSide={side !== 'self'}
        // Reused job cannot edit any variables
        readonly={isCurrNodeReused}
        message={isCurrNodeReused ? t('workflow.msg_resued_job_cannot_edit') : ''}
        toggleVisible={toggleDrawerVisible}
        showPeerConfigButton={side === 'self' && !workflow.is_local && Boolean(peerConfigValue)}
        currentIdx={currNode?.data.index}
        nodesCount={targetChartRef?.nodes.length || 0}
        jobDefinition={currNode?.data.raw}
        initialValues={currNodeVars}
        onGoNextJob={onGoNextJob}
        onCloseDrawer={onCloseDrawer}
        onViewPeerConfigClick={onViewPeerConfigClick}
      />

      <InspectPeerConfigs
        config={peerConfigValue}
        visible={peerCfgVisible}
        toggleVisible={togglePeerCfgVisible}
      />

      <footer className={styled.footer}>
        <GridRow gap="12">
          <Button type="primary" loading={submitting} onClick={submitToPatch}>
            {t('workflow.btn_submit_edit')}
          </Button>
          <Button onClick={onPrevStepClick} {...isDisabled}>
            {t('previous_step')}
          </Button>
          <Button onClick={onCancelEditClick} {...isDisabled}>
            {t('cancel')}
          </Button>
        </GridRow>
      </footer>
    </ErrorBoundary>
  );

  // --------- Methods ---------------
  function getConfigValueState(side: Side) {
    return ({
      self: [configValue, setConfigValue],
      peer: [peerConfigValue, setPeerConfigValue],
    } as const)[side];
  }
  function getChartRef(side: Side) {
    return ({
      self: selfConfigChartRef.current,
      peer: peerConfigChartRef.current,
    } as const)[side];
  }
  function checkIfAllJobConfigCompleted() {
    const allNodes =
      selfConfigChartRef.current?.nodes.concat(peerConfigChartRef.current?.nodes || []) || [];

    const isAllCompleted = allNodes.every((node: ChartNode) => {
      // Whether a node has Success status or it's been disabled
      // we recognize it as complete!
      return node.data.status === ChartNodeStatus.Success || node.data.disabled;
    });

    return isAllCompleted;
  }

  async function saveCurrentValues() {
    const values = await drawerRef.current?.getFormValues();

    const [innerConfigValue, setInnerConfigValue] = getConfigValueState(side);

    const nextValue = cloneDeep(innerConfigValue);

    if (currNode?.type === 'global') {
      // Hydrate values to workflow global variables
      nextValue.variables = hydrate(nextValue.variables, values) as Variable[];
    }

    if (currNode?.type === 'edit') {
      // Hydrate values to target job
      const targetJob = nextValue.job_definitions.find((job) => job.name === currNode.id);
      if (targetJob) {
        targetJob.variables = hydrate(targetJob.variables, values) as Variable[];
      }
    }

    setInnerConfigValue(nextValue as any);

    if (side === 'peer') {
      isChangedPeerConfigValue.current = true;
    }
  }
  async function validateCurrentValues() {
    if (!currNode) return;
    const isValid = await drawerRef.current?.validateCurrentForm();
    targetChartRef?.updateNodeStatusById({
      id: currNode.id,
      status: isValid ? ChartNodeStatus.Success : ChartNodeStatus.Warning,
    });
  }
  /** 🚀 Initiate patch request */
  async function submitToPatch() {
    if (!checkIfAllJobConfigCompleted()) {
      return Message.warning(i18n.t('workflow.msg_config_unfinished'));
    }

    toggleDrawerVisible(false);
    setSubmitting(true);

    if (isChangedPeerConfigValue.current) {
      const peerPayload = stringifyComplexDictField({
        config: peerConfigValue,
      } as WorkflowAcceptPayload);

      const [, error] = await to(
        patchPeerWorkflow(params.id, peerPayload as any, workflow.project_id),
      );

      if (error) {
        Message.error(error.message);
      }
    }

    const payload = stringifyComplexDictField({
      config: configValue,
      forkable: basicPayload.forkable!,
      cron_config: basicPayload.cron_config!,
    } as WorkflowAcceptPayload);

    payload.template_id = template?.id || workflow.template_info?.id;

    payload.template_revision_id = template?.revision_id;

    const [, error] = await to(patchWorkflow(params.id, payload, workflow.project_id));

    setSubmitting(false);

    if (!error) {
      setWorkflow(null as any);
      history.push('/workflow-center/workflows');
    } else {
      Message.error(error.message);
    }
  }
  async function selectNode(nextNode: ChartNode, nextSide: Side) {
    // If change one-side's job chart to another-side deselect current side's ndoe firstly
    targetChartRef?.setSelectedNodes([]);

    // Since setState is Asynchronous, we need manually get the targetRef instead of using predefined one
    const nextTargetChartRef = getChartRef(nextSide);

    const prevNode = currNode;
    if (currNode && prevNode) {
      // Validate & Save current form before go another job
      await validateCurrentValues();
      await saveCurrentValues();
    }

    // Turn target node status to configuring
    nextTargetChartRef?.updateNodeStatusById({
      id: nextNode.id,
      status: ChartNodeStatus.Processing,
    });

    setCurrNode(nextNode);

    nextTargetChartRef?.setSelectedNodes([nextNode]);

    toggleDrawerVisible(true);

    // Put setSide at the end to prevent previous codes from being confused by side-state
    setSide(nextSide);
  }

  // ---------- Handlers ----------------
  async function onCanvasClick() {
    if (!drawerVisible) return;
    await validateCurrentValues();
    saveCurrentValues();
    toggleDrawerVisible(false);
  }
  async function onCloseDrawer() {
    await validateCurrentValues();
    saveCurrentValues();
    targetChartRef?.setSelectedNodes([]);
  }
  function onGoNextJob() {
    if (!currNode) return;

    const nextNodeToSelect = targetChartRef?.nodes.find(
      (node: ChartNode) => node.data.index === currNode.data.index + 1,
    );
    nextNodeToSelect && selectNode(nextNodeToSelect, side);
  }
  function onPrevStepClick() {
    history.goBack();
  }

  function onNodeDisabledChange(
    _: string,
    { data, ...payload }: { id: string; data: NodeData; disabled: boolean },
  ) {
    const sideOfNode = data.side as Side;
    if (!sideOfNode) {
      console.error('[WorkflowEditStepTwoConfig]: assign a `side` prop to chart under forking');
      return;
    }
    getChartRef(sideOfNode)?.updateNodeDisabledById(payload);
  }

  function onCancelEditClick() {
    Modal.confirm({
      title: i18n.t('workflow.msg_sure_2_cancel_edit'),
      content: i18n.t('workflow.msg_sure_2_exist_edit'),
      onOk() {
        // if new tab only open this page，no other page has been opened，then go to workflows list page
        if (history.length <= 3) {
          history.push('/workflow-center/workflows');
          return;
        }
        history.go(-2);
      },
    });
  }
  function onViewPeerConfigClick() {
    togglePeerCfgVisible(true);
  }
};

function _markJobFlags(jobs: JobNodeRawData[], flags: CreateJobFlag[] = []) {
  if (!flags) return jobs;

  return jobs.map((item, index) => {
    if (flags[index] === CreateJobFlag.REUSE) {
      item.reused = true;
    }
    if (flags[index] === CreateJobFlag.DISABLED) {
      item.disabled = true;
    }

    return item;
  });
}

export default WorkflowEditStepTwoConfig;
