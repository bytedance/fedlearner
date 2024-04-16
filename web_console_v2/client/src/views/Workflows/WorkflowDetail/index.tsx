import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { Card, Spin, Row, Button, Col } from 'antd';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { getPeerWorkflowsConfig, getWorkflowDetailById } from 'services/workflow';
import WorkflowJobsCanvas from 'components/WorkflowJobsCanvas';
import { useTranslation } from 'react-i18next';
import WhichProject from 'components/WhichProject';
import WorkflowActions from '../WorkflowActions';
import WorkflowStage from '../WorkflowList/WorkflowStage';
import GridRow from 'components/_base/GridRow';
import BreadcrumbLink from 'components/BreadcrumbLink';
import CountTime from 'components/CountTime';
import JobExecutionDetailsDrawer from './JobExecutionDetailsDrawer';
import { useToggle } from 'react-use';
import { JobNode, NodeData, JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import { useMarkFederatedJobs } from 'components/WorkflowJobsCanvas/hooks';
import PropertyList from 'components/PropertyList';
import { Eye, EyeInvisible, Branch } from 'components/IconPark';
import { WorkflowExecutionDetails } from 'typings/workflow';
import { ReactFlowProvider } from 'react-flow-renderer';
import { findJobExeInfoByJobDef, isRunning, isStopped } from 'shared/workflow';
import dayjs from 'dayjs';
import NoResult from 'components/NoResult';
import { CreateJobFlag } from 'typings/job';
import SharedPageLayout from 'components/SharedPageLayout';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  height: var(--contentMinHeight);
`;
const ChartSection = styled.section`
  display: flex;
  margin-top: 12px;
  flex: 1;
`;
const ChartContainer = styled.div`
  height: 100%;
  flex: 1;

  & + & {
    margin-left: 16px;
  }
`;
const HeaderRow = styled(Row)`
  margin-bottom: 15px;

  &[data-forked='true'] {
    margin-bottom: 25px;
  }
`;
const Name = styled.h3`
  margin-bottom: 0;
  font-size: 20px;
  line-height: 1;
`;
const ForkedFrom = styled.div`
  margin-top: -20px;
  font-size: 12px;
`;
const OriginWorkflowLink = styled(Link)`
  margin-left: 5px;
`;
// TODO: find a better way to define no-result's container
const NoJobs = styled.div`
  display: flex;
  height: calc(100% - 48px);
  background-color: var(--gray1);
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

  &::after {
    margin-left: 25px;
    content: attr(data-note);
    font-size: 12px;
    color: var(--darkGray6);
  }
`;

const WorkflowDetail: FC = () => {
  const { t } = useTranslation();
  const params = useParams<{ id: string }>();
  const [peerJobsVisible, togglePeerJobsVisible] = useToggle(false);
  const [drawerVisible, toggleDrawerVisible] = useToggle(false);
  const [isPeerSide, setIsPeerSide] = useState(false);
  const [data, setData] = useState<NodeData>();

  const detailQuery = useQuery(
    ['getWorkflowDetailById', params.id],
    () => getWorkflowDetailById(params.id),
    { cacheTime: 1 },
  );
  const peerWorkflowQuery = useQuery(['getPeerWorkflow', params.id], getPeerWorkflow, {
    retry: false,
  });

  const workflow = detailQuery.data?.data;
  const peerWorkflow = peerWorkflowQuery.data;

  const isForked = Boolean(workflow?.forked_from);

  const originWorkflowQuery = useQuery(
    ['getPeerWorkflow', workflow?.forked_from],
    () => getWorkflowDetailById(workflow?.forked_from!),
    { enabled: isForked },
  );

  let isRunning_ = false;
  let isStopped_ = false;

  let runningTime: number = 0;

  if (workflow) {
    isRunning_ = isRunning(workflow);
    isStopped_ = isStopped(workflow);

    if (isRunning_ || isStopped_) {
      const { stop_at, start_at } = workflow;
      runningTime = isStopped_ ? stop_at! - start_at! : dayjs().unix() - start_at!;
    }
  }

  const workflowProps = [
    {
      label: t('workflow.label_template_name'),
      value: workflow?.config?.group_alias || (
        <Link to={`/workflows/accept/basic/${workflow?.id}`}>{t('workflow.job_node_pending')}</Link>
      ),
    },
    {
      label: t('workflow.label_project'),
      value: <WhichProject id={workflow?.project_id || 0} />,
    },
    {
      label: t('workflow.label_running_time'),

      value: Boolean(workflow) && <CountTime time={runningTime} isStatic={!isRunning_} />,
    },
    {
      label: t('workflow.label_batch_update_interval'),
      value: `${workflow?.batch_update_interval} min`,
      hidden: !workflow?.batch_update_interval || workflow?.batch_update_interval === -1,
    },
    // Display workflow global variables
    ...(workflow?.config?.variables || []).map((item) => ({ label: item.name, value: item.value })),
  ];

  const { markThem } = useMarkFederatedJobs();

  let jobsWithExeDetails = _mergeWithExecutionDetails(workflow);
  let peerJobsWithExeDetails = _mergeWithExecutionDetails(peerWorkflowQuery.data);
  jobsWithExeDetails = _markJobFlags(jobsWithExeDetails, workflow?.create_job_flags!);
  peerJobsWithExeDetails = _markJobFlags(peerJobsWithExeDetails, workflow?.peer_create_job_flags!);

  markThem(jobsWithExeDetails, peerJobsWithExeDetails);

  return (
    <SharedPageLayout
      title={
        <BreadcrumbLink
          paths={[
            { label: 'menu.label_workflow', to: '/workflows' },
            { label: 'workflow.execution_detail' },
          ]}
        />
      }
      contentWrapByCard={false}
    >
      <Spin spinning={detailQuery.isLoading}>
        <Container>
          <Card>
            <HeaderRow justify="space-between" align="middle" data-forked={isForked}>
              <GridRow gap="8">
                <Name>{workflow?.name}</Name>

                {workflow && <WorkflowStage workflow={workflow} tag />}
              </GridRow>
              {workflow && (
                <Col>
                  <WorkflowActions workflow={workflow} onSuccess={detailQuery.refetch} />
                </Col>
              )}
            </HeaderRow>

            {isForked && originWorkflowQuery.isSuccess && (
              <ForkedFrom>
                <Branch />
                {t('workflow.forked_from')}
                <OriginWorkflowLink to={`/workflows/${originWorkflowQuery.data?.data.id}`}>
                  {originWorkflowQuery.data?.data.name}
                </OriginWorkflowLink>
              </ForkedFrom>
            )}

            <PropertyList
              labelWidth={100}
              initialVisibleRows={3}
              cols={3}
              properties={workflowProps}
              style={{ marginBottom: '0' }}
            />
          </Card>

          <ChartSection>
            {/* Our config */}
            <ChartContainer>
              <ChartHeader justify="space-between" align="middle">
                <ChartTitle data-note={peerJobsVisible ? t('workflow.federated_note') : ''}>
                  {t('workflow.our_config')}
                </ChartTitle>

                {!peerJobsVisible && (
                  <Button icon={<Eye />} onClick={() => togglePeerJobsVisible(true)}>
                    {t('workflow.btn_see_peer_config')}
                  </Button>
                )}
              </ChartHeader>

              {jobsWithExeDetails.length === 0 ? (
                <NoJobs>
                  <NoResult
                    text={t('workflow.msg_not_config')}
                    CTAText={t('workflow.action_configure')}
                    to={`/workflows/accept/basic/${params.id}`}
                  />
                </NoJobs>
              ) : (
                <ReactFlowProvider>
                  <WorkflowJobsCanvas
                    nodeType="execution"
                    workflowConfig={{
                      ...workflow?.config!,
                      job_definitions: jobsWithExeDetails,
                      variables: [],
                    }}
                    onJobClick={viewJobDetail}
                    onCanvasClick={() => toggleDrawerVisible(false)}
                  />
                </ReactFlowProvider>
              )}
            </ChartContainer>

            {/* Peer config */}
            {peerJobsVisible && (
              <ChartContainer>
                <ChartHeader justify="space-between" align="middle">
                  <ChartTitle data-note={peerJobsVisible ? t('workflow.federated_note') : ''}>
                    {t('workflow.peer_config')}
                  </ChartTitle>

                  <Button icon={<EyeInvisible />} onClick={() => togglePeerJobsVisible(false)}>
                    {t('workflow.btn_hide_peer_config')}
                  </Button>
                </ChartHeader>

                {peerJobsWithExeDetails.length === 0 ? (
                  <NoJobs>
                    {peerWorkflowQuery.isFetching ? (
                      <Spin style={{ margin: 'auto' }} />
                    ) : (
                      <NoResult text={t('workflow.msg_peer_not_ready')} />
                    )}
                  </NoJobs>
                ) : (
                  <ReactFlowProvider>
                    <WorkflowJobsCanvas
                      nodeType="execution"
                      workflowConfig={{
                        ...peerWorkflowQuery.data?.config!,
                        job_definitions: peerJobsWithExeDetails,
                        variables: [],
                      }}
                      onJobClick={viewPeerJobDetail}
                      onCanvasClick={() => toggleDrawerVisible(false)}
                    />
                  </ReactFlowProvider>
                )}
              </ChartContainer>
            )}
          </ChartSection>

          <JobExecutionDetailsDrawer
            key="self"
            visible={drawerVisible && !isPeerSide}
            toggleVisible={toggleDrawerVisible}
            jobData={data}
            workflow={workflow}
          />

          <JobExecutionDetailsDrawer
            key="peer"
            visible={drawerVisible && isPeerSide}
            toggleVisible={toggleDrawerVisible}
            jobData={data}
            placement="left"
            workflow={peerWorkflow}
            isPeerSide
          />
        </Container>
      </Spin>
    </SharedPageLayout>
  );

  function viewJobDetail(jobNode: JobNode) {
    setIsPeerSide(false);
    showJobDetailesDrawer(jobNode);
  }
  function viewPeerJobDetail(jobNode: JobNode) {
    setIsPeerSide(true);
    showJobDetailesDrawer(jobNode);
  }
  function showJobDetailesDrawer(jobNode: JobNode) {
    setData(jobNode.data);
    toggleDrawerVisible(true);
  }
  async function getPeerWorkflow() {
    const res = await getPeerWorkflowsConfig(params.id);
    const anyPeerWorkflow = Object.values(res.data).find((item) => !!item.config)!;

    return anyPeerWorkflow;
  }
};

function _mergeWithExecutionDetails(workflow?: WorkflowExecutionDetails): JobNodeRawData[] {
  if (!workflow) return [];

  return (
    workflow.config?.job_definitions.map((item) => {
      const exeInfo = findJobExeInfoByJobDef(item, workflow);

      return {
        ...item,
        ...exeInfo,
        name: item.name,
        k8sName: exeInfo?.name,
      } as JobNodeRawData;
    }) || []
  );
}

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

export default WorkflowDetail;
