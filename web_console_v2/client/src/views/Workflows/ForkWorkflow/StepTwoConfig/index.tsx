import { Button, Message, Grid, Spin } from '@arco-design/web-react';
import Modal from 'components/Modal';
import WorkflowJobsCanvas, { ChartExposedRef } from 'components/WorkflowJobsCanvas';
import { useMarkFederatedJobs } from 'components/WorkflowJobsCanvas/hooks';
import { WORKFLOW_JOB_NODE_CHANNELS } from 'components/WorkflowJobsCanvas/JobNodes/shared';
import {
  ChartNode,
  ChartNodes,
  ChartNodeStatus,
  JobNodeRawData,
  NodeData,
} from 'components/WorkflowJobsCanvas/types';
import GridRow from 'components/_base/GridRow';
import { useSubscribe } from 'hooks';
import i18n from 'i18n';
import { cloneDeep, omit } from 'lodash-es';
import React, { FC, useRef, useState } from 'react';
import { ReactFlowProvider } from 'react-flow-renderer';
import { useTranslation } from 'react-i18next';
import { useQuery } from 'react-query';
import { Redirect, useHistory, useParams } from 'react-router-dom';
import { useToggle } from 'react-use';
import { useRecoilState } from 'recoil';
import {
  forkTheWorkflow,
  getPeerWorkflow,
  getWorkflowDetailById,
  PEER_WORKFLOW_DETAIL_QUERY_KEY,
} from 'services/workflow';
import { parseComplexDictField, stringifyComplexDictField } from 'shared/formSchema';
import { to } from 'shared/helpers';
import { forkWorkflowForm } from 'stores/workflow';
import styled from './index.module.less';
import { Side } from 'typings/app';
import { CreateJobFlag } from 'typings/job';
import { ChartWorkflowConfig } from 'typings/workflow';
import LocalWorkflowNote from 'views/Workflows/LocalWorkflowNote';
import JobFormDrawer, { JobFormDrawerExposedRef } from '../../JobFormDrawer';
import { hydrate } from 'views/Workflows/shared';
import { Variable } from 'typings/variable';

const Row = Grid.Row;

// We only have two side so far
const ALL_SIDES: Side[] = ['self', 'peer'];

const WorkflowForkStepTwoConfig: FC = () => {
  const { t } = useTranslation();
  const history = useHistory();
  const params = useParams<{ id: string }>();
  const [currNode, setCurrNode] = useState<ChartNode>();
  const [submitting, setSubmitting] = useToggle(false);
  const [side, setSide] = useState<Side>('self');
  const drawerRef = useRef<JobFormDrawerExposedRef>();
  const selfConfigChartRef = useRef<ChartExposedRef>();
  const peerConfigChartRef = useRef<ChartExposedRef>();
  const [drawerVisible, toggleDrawerVisible] = useToggle(false);

  const [formData, setFormData] = useRecoilState(forkWorkflowForm);

  const { markThem } = useMarkFederatedJobs();

  const selfQuery = useQuery(['getWorkflow', params.id], () => getWorkflowDetailById(params.id), {
    refetchOnWindowFocus: false,
    onSuccess(data) {
      const config = parseComplexDictField(data.data).config! as ChartWorkflowConfig;

      markThem(config.job_definitions);

      setFormData({
        ...formData,
        config,
      });
    },
  });

  const peerQuery = useQuery(
    [PEER_WORKFLOW_DETAIL_QUERY_KEY, params.id],
    () => getPeerWorkflow(params.id),
    {
      refetchOnWindowFocus: false,
      enabled: !formData.is_local && !selfQuery.isFetching,
      onSuccess(data) {
        const fork_proposal_config = parseComplexDictField(data).config! as ChartWorkflowConfig;
        markThem(fork_proposal_config.job_definitions);

        setFormData({
          ...formData,
          fork_proposal_config,
        });
      },
    },
  );

  useSubscribe(WORKFLOW_JOB_NODE_CHANNELS.change_inheritance, onNodeInheritanceChange);
  useSubscribe(WORKFLOW_JOB_NODE_CHANNELS.disable_job, onNodeDisabledChange);

  if (peerQuery.data?.forkable === false) {
    Message.warning(t('workflow.msg_unforkable'));
    return <Redirect to={'/workflow-center/workflows'} />;
  }

  if (selfQuery.isFetching || peerQuery.isFetching) {
    return (
      <div className={styled.loadind_container}>
        <Spin />
      </div>
    );
  }

  const targetConfigKey = getConfigKey(side);
  const targetChartRef = getChartRef(side);

  const currNodeValues =
    currNode?.type === 'global'
      ? formData[targetConfigKey].variables
      : formData[targetConfigKey].job_definitions.find((item) => item.name === currNode?.id)
          ?.variables;

  const isDisabled = { disabled: submitting };

  return (
    <>
      <section className={styled.chart_section}>
        <div className={styled.chart_container}>
          <Row className={styled.chart_header} justify="space-between" align="center">
            <h3 className={styled.chart_title}>{t('workflow.our_config')}</h3>
            {formData.is_local && <LocalWorkflowNote />}
          </Row>
          <ReactFlowProvider>
            <WorkflowJobsCanvas
              ref={selfConfigChartRef}
              side="self"
              nodeType="fork"
              nodeInitialStatus={ChartNodeStatus.Success}
              workflowConfig={formData.config}
              onCanvasClick={onCanvasClick}
              onJobClick={(node) => selectNode(node, 'self')}
            />
          </ReactFlowProvider>
        </div>

        {!formData.is_local && formData.fork_proposal_config && (
          <div className={styled.chart_container}>
            <Row className={styled.chart_header} justify="space-between" align="center">
              <h3 className={styled.chart_title}>{t('workflow.peer_config')}</h3>
            </Row>

            <ReactFlowProvider>
              <WorkflowJobsCanvas
                ref={peerConfigChartRef}
                side="peer"
                nodeType="fork"
                nodeInitialStatus={ChartNodeStatus.Success}
                workflowConfig={formData.fork_proposal_config}
                onCanvasClick={onCanvasClick}
                onJobClick={(node) => selectNode(node, 'peer')}
              />
            </ReactFlowProvider>
          </div>
        )}

        <JobFormDrawer
          ref={drawerRef as any}
          isPeerSide={side !== 'self'}
          visible={drawerVisible}
          currentIdx={currNode?.data.index}
          nodesCount={targetChartRef?.nodes.length || 0}
          jobDefinition={currNode?.data.raw}
          initialValues={currNodeValues}
          onGoNextJob={onGoNextJob}
          onCloseDrawer={onCloseDrawer}
          toggleVisible={toggleDrawerVisible}
        />
      </section>

      <footer className={styled.footer}>
        <GridRow gap="12">
          <Button type="primary" loading={submitting} onClick={submitToFork}>
            {formData.is_local ? '复制工作流' : t('workflow.btn_send_2_ptcpt')}
          </Button>
          <Button onClick={onPrevStepClick} {...isDisabled}>
            {t('previous_step')}
          </Button>
          <Button onClick={onCancelForkClick} {...isDisabled}>
            {t('cancel')}
          </Button>
        </GridRow>
      </footer>
    </>
  );

  // ----------- Methods --------------
  function getConfigKey(side: Side) {
    return ({
      self: 'config',
      peer: 'fork_proposal_config',
    } as const)[side];
  }
  function getChartRef(side: Side) {
    return ({
      self: selfConfigChartRef.current,
      peer: peerConfigChartRef.current,
    } as const)[side];
  }
  async function selectNode(nextNode: ChartNode, nextSide: Side) {
    // If change one-side's job chart to another-side deselect current side's ndoe firstly
    targetChartRef?.setSelectedNodes([]);

    // Since setState is Asynchronous, we need manually get the targetRef instead of using predefined one
    const nextTargetChartRef = getChartRef(nextSide);

    const prevData = currNode?.data;
    if (currNode && prevData) {
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
  async function validateCurrentValues() {
    if (!currNode) return;
    const isValid = await drawerRef.current?.validateCurrentForm();
    targetChartRef?.updateNodeStatusById({
      id: currNode.id,
      status: isValid ? ChartNodeStatus.Success : ChartNodeStatus.Warning,
    });
  }
  async function saveCurrentValues() {
    const values = await drawerRef.current?.getFormValues();

    const nextValue = cloneDeep(formData);

    if (currNode?.type === 'global') {
      // Hydrate values to workflow global variables
      nextValue[targetConfigKey].variables = hydrate(
        nextValue[targetConfigKey].variables,
        values,
      ) as Variable[];
    }

    if (currNode?.type === 'fork') {
      // Hydrate values to target job
      const targetJob = nextValue[targetConfigKey].job_definitions.find(
        (job) => job.name === currNode.id,
      );
      if (targetJob) {
        targetJob.variables = hydrate(targetJob.variables, values) as Variable[];
      }
    }

    setFormData(nextValue);
  }
  function checkIfAllJobConfigCompleted() {
    const allNodes =
      selfConfigChartRef.current?.nodes.concat(peerConfigChartRef.current?.nodes || []) || [];

    const isAllCompleted = allNodes.every((node) => {
      return node.data.status === ChartNodeStatus.Success || node.data.disabled;
    });

    return isAllCompleted;
  }
  /** 🚀 Initiate fork request */
  async function submitToFork() {
    if (!checkIfAllJobConfigCompleted()) {
      return Message.warning(i18n.t('workflow.msg_config_unconfirm_or_unfinished'));
    }
    toggleDrawerVisible(false);

    setSubmitting(true);

    const payload = stringifyComplexDictField(formData);

    // Omit unused props
    payload.config.job_definitions = _omitJobsColorMark(payload.config.job_definitions);
    // Find reusable job names for both peer and self side
    payload.create_job_flags = _mapJobFlags(selfConfigChartRef.current?.nodes!);

    // If not local workflow, do same things to peer side
    if (!formData.is_local) {
      payload.peer_create_job_flags = _mapJobFlags(peerConfigChartRef.current?.nodes!);
      payload.fork_proposal_config.job_definitions = _omitJobsColorMark(
        payload.fork_proposal_config.job_definitions,
      );
    }

    const [, error] = await to(forkTheWorkflow(payload, payload.project_id));

    setSubmitting(false);

    if (!error) {
      history.push('/workflow-center/workflows');
    } else {
      Message.error(error.message);
    }
  }
  // ------------ Handlers -------------
  function onCancelForkClick() {
    Modal.confirm({
      title: i18n.t('workflow.msg_sure_2_cancel_fork'),
      content: i18n.t('workflow.msg_effect_of_cancel_create'),
      onOk() {
        history.push('/workflow-center/workflows');
      },
    });
  }
  async function onCanvasClick() {
    toggleDrawerVisible(false);
    await validateCurrentValues();
    saveCurrentValues();
    targetChartRef?.setSelectedNodes([]);
  }
  function onPrevStepClick() {
    history.goBack();
  }
  function onGoNextJob() {
    if (!currNode) return;

    const nextNodeToSelect = targetChartRef?.nodes.find(
      (node) => node.data.index === currNode.data.index + 1,
    );

    nextNodeToSelect && selectNode(nextNodeToSelect, side);
  }
  async function onCloseDrawer() {
    await validateCurrentValues();
    saveCurrentValues();
    targetChartRef?.setSelectedNodes([]);
  }

  function onNodeDisabledChange(
    _: string,
    payload: { id: string; data: NodeData; disabled: boolean },
  ) {
    const sideOfNode = payload.data.side as Side;
    if (!sideOfNode) {
      console.error('[WorkflowForkStepTwoConfig]: assign a `side` prop to chart under forking');
      return;
    }

    const targetSides = payload.data.raw.is_federated ? ALL_SIDES : [sideOfNode];

    targetSides.forEach((side) => {
      getChartRef(side)?.updateNodeDisabledById({
        id: payload.id, // federated jobs share the same name/id
        disabled: payload.disabled,
      });
    });
  }
  function onNodeInheritanceChange(
    _: any,
    payload: { id: string; data: NodeData; whetherInherit: boolean },
  ) {
    const sideOfNode = payload.data.side as Side;
    if (!sideOfNode) {
      console.error('[WorkflowForkStepTwoConfig]: assign a `side` prop to chart under forking');
      return;
    }
    const targetSides = payload.data.raw.is_federated ? ALL_SIDES : [sideOfNode];

    targetSides.forEach((side) => {
      getChartRef(side)?.updateNodeInheritanceById({
        id: payload.id, // federated jobs share the same name/id
        whetherInherit: payload.whetherInherit,
      });
    });
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

      if (node.data.inherited) {
        return CreateJobFlag.REUSE;
      }

      return CreateJobFlag.NEW;
    });
}

function _omitJobsColorMark(jobs: JobNodeRawData[]): JobNodeRawData[] {
  return jobs.map((job) => omit(job, 'mark'));
}

export default WorkflowForkStepTwoConfig;
