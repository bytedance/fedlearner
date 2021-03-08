import React, { FC, useState, useRef } from 'react';
import { Row, Modal, Button, message, Spin } from 'antd';
import { useQuery } from 'react-query';
import { Redirect, useHistory, useParams } from 'react-router-dom';
import { useRecoilState } from 'recoil';
import { forkTheWorkflow, getPeerWorkflowsConfig, getWorkflowDetailById } from 'services/workflow';
import { forkWorkflowForm } from 'stores/workflow';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { ReactFlowProvider } from 'react-flow-renderer';
import WorkflowJobsFlowChart, { ChartExposedRef } from 'components/WorkflowJobsFlowChart';
import {
  ChartNode,
  ChartNodes,
  ChartNodeStatus,
  NodeData,
  NodeDataRaw,
} from 'components/WorkflowJobsFlowChart/types';
import { useMarkFederatedJobs } from 'components/WorkflowJobsFlowChart/hooks';
import { cloneDeep, Dictionary, omit } from 'lodash';
import JobFormDrawer, { JobFormDrawerExposedRef } from '../../JobFormDrawer';
import { useToggle } from 'react-use';
import { WorkflowExecutionDetails, ChartWorkflowConfig } from 'typings/workflow';
import { Variable } from 'typings/variable';
import { parseWidgetSchemas, stringifyWidgetSchemas } from 'shared/formSchema';
import i18n from 'i18n';
import { ExclamationCircle } from 'components/IconPark';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import GridRow from 'components/_base/GridRow';
import { to } from 'shared/helpers';
import { MixinFlexAlignCenter } from 'styles/mixins';
import { useSubscribe } from 'hooks';
import { WORKFLOW_JOB_NODE_CHANNELS } from 'components/WorkflowJobsFlowChart/WorkflowJobNode';

const LoadingContainer = styled.div`
  ${MixinFlexAlignCenter()}

  display: flex;
  height: 100%;
  background-color: white;
`;
const ChartSection = styled.section`
  position: relative;
  display: flex;
  height: 100%;
`;
const ChartContainer = styled.div`
  height: 100%;
  flex: 1;

  & + & {
    margin-left: 16px;
  }
`;
const ChartHeader = styled(Row)`
  height: 48px;
  padding: 0 20px;
  font-size: 14px;
  line-height: 22px;
  background-color: white;
`;
const ChartTitle = styled.h3`
  margin-bottom: 0;
`;
const Footer = styled.footer`
  position: sticky;
  bottom: 0;
  z-index: 5; // just above react-flow' z-index
  padding: 15px 36px;
  background-color: white;
`;

// We only have two side so far
type Side = 'self' | 'peer';
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

  useQuery(['getWorkflow', params.id], () => getWorkflowDetailById(params.id), {
    refetchOnWindowFocus: false,
    onSuccess(data) {
      const config = parseWidgetSchemas(data.data).config! as ChartWorkflowConfig;

      setFormData({
        ...formData,
        config,
      });
    },
  });
  const peerQuery = useQuery(['getPeerWorkflow', params.id], getPeerWorkflow, {
    refetchOnWindowFocus: false,
    onSuccess(data) {
      const fork_proposal_config = parseWidgetSchemas(data).config! as ChartWorkflowConfig;
      markThem(fork_proposal_config.job_definitions);

      setFormData({
        ...formData,
        fork_proposal_config,
      });
    },
  });

  useSubscribe(WORKFLOW_JOB_NODE_CHANNELS.change_inheritance, onNodeInheritanceChange);

  if (peerQuery.data?.forkable === false) {
    message.warning(t('workflow.msg_unforkable'));
    return <Redirect to={'/workflows'} />;
  }

  if (!formData.config || !formData.fork_proposal_config) {
    return (
      <LoadingContainer>
        <Spin />
      </LoadingContainer>
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
      <ChartSection>
        <ChartContainer>
          <ChartHeader justify="space-between" align="middle">
            <ChartTitle>{t('workflow.our_config')}</ChartTitle>
          </ChartHeader>
          <ReactFlowProvider>
            <WorkflowJobsFlowChart
              ref={selfConfigChartRef}
              side="self"
              nodeType="fork"
              workflowConfig={formData.config}
              onCanvasClick={onCanvasClick}
              onJobClick={(node) => selectNode(node, 'self')}
            />
          </ReactFlowProvider>
        </ChartContainer>

        <ChartContainer>
          <ChartHeader justify="space-between" align="middle">
            <ChartTitle>{t('workflow.peer_config')}</ChartTitle>
          </ChartHeader>

          <ReactFlowProvider>
            <WorkflowJobsFlowChart
              ref={peerConfigChartRef}
              side="peer"
              nodeType="fork"
              workflowConfig={formData.fork_proposal_config}
              onCanvasClick={onCanvasClick}
              onJobClick={(node) => selectNode(node, 'peer')}
            />
          </ReactFlowProvider>
        </ChartContainer>

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
      </ChartSection>

      <Footer>
        <GridRow gap="12">
          <Button type="primary" loading={submitting} onClick={submitToFork}>
            {t('workflow.btn_send_2_ptcpt')}
          </Button>
          <Button onClick={onPrevStepClick} {...isDisabled}>
            {t('previous_step')}
          </Button>
          <Button onClick={onCancelForkClick} {...isDisabled}>
            {t('cancel')}
          </Button>
        </GridRow>
      </Footer>
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

  async function getPeerWorkflow(): Promise<WorkflowExecutionDetails> {
    const res = await getPeerWorkflowsConfig(params.id);
    const anyPeerWorkflow = Object.values(res.data).find((item) => !!item.config)!;

    return anyPeerWorkflow;
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

    let nextValue = cloneDeep(formData);

    if (currNode?.type === 'global') {
      // Hydrate values to workflow global variables
      nextValue[targetConfigKey].variables = _hydrate(nextValue[targetConfigKey].variables, values);
    }

    if (currNode?.type === 'fork') {
      // Hydrate values to target job
      const targetJob = nextValue[targetConfigKey].job_definitions.find(
        (job) => job.name === currNode.id,
      );
      if (targetJob) {
        targetJob.variables = _hydrate(targetJob.variables, values);
      }
    }

    setFormData(nextValue);
  }
  function checkIfAllJobConfigCompleted() {
    const allNodes =
      selfConfigChartRef.current?.nodes.concat(peerConfigChartRef.current?.nodes || []) || [];

    const isAllCompleted = allNodes.every((node) => {
      return node.data.status === ChartNodeStatus.Success;
    });

    return isAllCompleted;
  }
  /** 🚀 Initiate fork request */
  async function submitToFork() {
    if (!checkIfAllJobConfigCompleted()) {
      return message.warn(i18n.t('workflow.msg_config_unconfirm_or_unfinished'));
    }
    toggleDrawerVisible(false);

    setSubmitting(true);

    const payload = stringifyWidgetSchemas(formData);

    payload.config.job_definitions = _omitJobsColorMark(payload.config.job_definitions);

    payload.fork_proposal_config.job_definitions = _omitJobsColorMark(
      payload.fork_proposal_config.job_definitions,
    );

    // Find reusable job names for both peer and self side
    payload.reuse_job_names = _filterReusableJobs(selfConfigChartRef.current?.nodes!);
    payload.peer_reuse_job_names = _filterReusableJobs(peerConfigChartRef.current?.nodes!);

    // FIXME: remove after using hashed job name
    payload.name = payload.name.replace(/[\s]/g, '');

    const [, error] = await to(forkTheWorkflow(payload));

    setSubmitting(false);

    if (!error) {
      history.push('/workflows');
    } else {
      message.error(error.message);
    }
  }
  // ------------ Handlers -------------
  function onCancelForkClick() {
    Modal.confirm({
      title: i18n.t('workflow.msg_sure_2_cancel_fork'),
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
        id: payload.id, // federated jobs share the same name
        whetherInherit: payload.whetherInherit,
      });
    });
  }
};

function _hydrate(variableShells: Variable[], formValues?: Dictionary<any>): Variable[] {
  if (!formValues) return [];

  return variableShells.map((item) => {
    return {
      ...item,
      value: formValues[item.name],
    };
  });
}

function _filterReusableJobs(nodes: ChartNodes) {
  return nodes
    .filter((node) => node.data.inherit)
    .filter((node) => node.type !== 'global')
    .map((item) => item.id)!;
}

function _omitJobsColorMark(jobs: NodeDataRaw[]): NodeDataRaw[] {
  return jobs.map((job) => omit(job, 'mark'));
}

export default WorkflowForkStepTwoConfig;
