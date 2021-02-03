import React, { FC, useState, useRef } from 'react';
import { Row } from 'antd';
import { useQuery } from 'react-query';
import { useParams } from 'react-router-dom';
import { useRecoilState } from 'recoil';
import { getPeerWorkflowsConfig, getWorkflowDetailById } from 'services/workflow';
import { forkWorkflowForm } from 'stores/workflow';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { ReactFlowProvider } from 'react-flow-renderer';
import WorkflowJobsFlowChart, {
  updateNodeStatusById,
  ChartExposedRef,
} from 'components/WorkflowJobsFlowChart';
import { ChartNode, JobNodeStatus } from 'components/WorkflowJobsFlowChart/helpers';
import { noop } from 'lodash';
import JobFormDrawer, { JobFormDrawerExposedRef } from '../../JobFormDrawer';
import { useToggle } from 'react-use';

const ChartSection = styled.section`
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

const WorkflowForkStepTwoConfig: FC = () => {
  const { t } = useTranslation();
  const params = useParams<{ id: string }>();
  const [currNode, setCurrNode] = useState<ChartNode>();
  const drawerRef = useRef<JobFormDrawerExposedRef>();
  const selfConfigChartRef = useRef<ChartExposedRef>();
  const peerConfigChartRef = useRef<ChartExposedRef>();
  const [drawerVisible, toggleDrawerVisible] = useToggle(false);

  const [formData, setFormData] = useRecoilState(forkWorkflowForm);

  useQuery(['getPeerWorkflow', params.id], getPeerWorkflow, {
    refetchOnWindowFocus: false,
    onSuccess(data) {
      setFormData({
        ...formData,
        fork_proposal_config: data.config!,
      });
    },
  });

  useQuery(['getWorkflow', params.id], () => getWorkflowDetailById(params.id), {
    refetchOnWindowFocus: false,
    onSuccess(data) {
      setFormData({
        ...formData,
        config: data.data.config!,
      });
    },
  });

  return (
    <ChartSection>
      <ChartContainer>
        <ChartHeader justify="space-between" align="middle">
          <ChartTitle>{t('workflow.our_config')}</ChartTitle>
        </ChartHeader>
        <ReactFlowProvider>
          {formData.config && (
            <WorkflowJobsFlowChart
              ref={selfConfigChartRef}
              nodeType="config"
              workflowConfig={formData.config}
              onCanvasClick={() => noop(false)}
              onJobClick={selectNode}
            />
          )}
        </ReactFlowProvider>
      </ChartContainer>

      {/* <ChartContainer>
        <ChartHeader justify="space-between" align="middle">
          <ChartTitle>{t('workflow.peer_config')}</ChartTitle>
        </ChartHeader>

        <ReactFlowProvider>
          {formData.fork_proposal_config && (
            <WorkflowJobsFlowChart
              type="config"
              ref={peerConfigChartRef}
              onCanvasClick={() => noop(false)}
              jobs={formData.fork_proposal_config.job_definitions}
              globalVariables={formData.fork_proposal_config.variables}
              onJobClick={selectNode}
            />
          )}
        </ReactFlowProvider>
      </ChartContainer> */}

      {/* <JobFormDrawer
        ref={drawerRef as any}
        node={currNode!}
        visible={drawerVisible}
        toggleVisible={toggleDrawerVisible}
        onConfirm={selectNode}
        onCloseDrawer={noop}
        jobNodes={selfConfigChartRef.current?.nodes}
      /> */}
    </ChartSection>
  );

  async function getPeerWorkflow() {
    const res = await getPeerWorkflowsConfig(params.id);
    const anyPeerWorkflow = Object.values(res.data).find((item) => !!item.config)!;

    return anyPeerWorkflow;
  }
  async function selectNode(nextNode: ChartNode) {
    const prevData = currNode?.data;
    if (prevData) {
      // Validate & Save current form before go another job
      // await drawerRef.current?.saveCurrentValues();
      // await drawerRef.current?.validateCurrentJobForm();
    }

    // Turn target node status to configuring
    updateNodeStatusById({ id: nextNode.id, status: JobNodeStatus.Processing });

    setCurrNode(nextNode);

    selfConfigChartRef.current?.setSelectedNodes([nextNode]);

    toggleDrawerVisible(true);
  }
};

export default WorkflowForkStepTwoConfig;
