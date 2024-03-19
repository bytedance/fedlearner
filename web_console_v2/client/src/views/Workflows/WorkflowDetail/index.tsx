import React, { FC, useState, useMemo } from 'react';
import styled from './index.module.less';
import { Card, Spin, Grid, Button, Message } from '@arco-design/web-react';
import { useParams, Link, useHistory } from 'react-router-dom';
import { useQuery } from 'react-query';
import {
  getPeerWorkflow,
  getWorkflowDetailById,
  getWorkflowDownloadHref,
  PEER_WORKFLOW_DETAIL_QUERY_KEY,
} from 'services/workflow';
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
import { IconEye, IconEyeInvisible, IconBranch } from '@arco-design/web-react/icon';
import { Workflow, WorkflowExecutionDetails, WorkflowState } from 'typings/workflow';
import { ReactFlowProvider } from 'react-flow-renderer';
import { findJobExeInfoByJobDef } from 'shared/workflow';
import dayjs from 'dayjs';
import NoResult from 'components/NoResult';
import { CreateJobFlag } from 'typings/job';
import SharedPageLayout from 'components/SharedPageLayout';
import GlobalConfigDrawer from './GlobalConfigDrawer';
import LocalWorkflowNote from '../LocalWorkflowNote';
import request from 'libs/request';
import { saveBlob } from 'shared/helpers';
import { formatExtra } from 'shared/modelCenter';
import { VariablePermissionLegend } from 'components/VariblePermission';
import { parseCron } from 'components/CronTimePicker';
import { projectListQuery } from 'stores/project';
import { useRecoilQuery } from 'hooks/recoil';
import { TIME_INTERVAL, CONSTANTS } from 'shared/constants';
import ClickToCopy from 'components/ClickToCopy';
import { Tooltip } from '@arco-design/web-react';

const Row = Grid.Row;
const Col = Grid.Col;

const WorkflowDetail: FC = () => {
  const { t } = useTranslation();
  const history = useHistory();
  const params = useParams<{
    id: string;
    type?: 'model-management' | 'model-evaluation' | 'offline-prediction';
    /** dataset kind */
    kind_label?: 'raw' | 'processed';
  }>();
  const [peerJobsVisible, togglePeerJobsVisible] = useToggle(false);
  const [jobExecutionDetailsDrawerVisible, toggleJobExecutionDetailsDrawerVisible] = useToggle(
    false,
  );
  const [globalConfigDrawerVisible, toggleGlobalConfigDrawerVisible] = useToggle(false);

  const [isPeerSide, setIsPeerSide] = useState(false);
  const [data, setData] = useState<NodeData>();

  const detailQuery = useQuery(
    ['getWorkflowDetailById', params.id],
    () => getWorkflowDetailById(params.id),
    { cacheTime: 1, refetchInterval: TIME_INTERVAL.CONNECTION_CHECK },
  );

  const { data: projectList } = useRecoilQuery(projectListQuery);

  const workflow = detailQuery.data?.data;

  const isForked = Boolean(workflow?.forked_from);
  const isLocalRun = Boolean(workflow?.is_local);

  const peerWorkflowQuery = useQuery(
    [PEER_WORKFLOW_DETAIL_QUERY_KEY, params.id],
    () => getPeerWorkflow(params.id),
    {
      retry: false,
      enabled: Boolean(workflow) && !isLocalRun, // Wait for workflow response
    },
  );
  const peerWorkflow = peerWorkflowQuery.data;

  const originWorkflowQuery = useQuery(
    ['getWorkflowDetailById', workflow?.forked_from],
    () => getWorkflowDetailById(workflow?.forked_from!),
    { enabled: isForked },
  );

  const { RUNNING, STOPPED, COMPLETED, FAILED } = WorkflowState;

  let isRunning_ = false;
  let isStopped_ = false;

  let runningTime: number = 0;

  if (workflow) {
    const { state } = workflow;
    isRunning_ = state === RUNNING;
    isStopped_ = [STOPPED, COMPLETED, FAILED].includes(state);

    if (isRunning_ || isStopped_) {
      const { stop_at, start_at } = workflow;
      runningTime = isStopped_ ? stop_at! - start_at! : dayjs().unix() - start_at!;
    }
  }
  async function onDownloadTemplate() {
    try {
      const blob = await request(
        getWorkflowDownloadHref(workflow?.id || '', workflow?.project_id),
        {
          responseType: 'blob',
        },
      );
      saveBlob(blob, `${workflow?.name}使用模板.json`);
    } catch (error: any) {
      Message.error(error.message);
    }
  }
  const workflowProps = [
    {
      label: t('workflow.label_uuid'),
      value: workflow?.uuid ?? CONSTANTS.EMPTY_PLACEHOLDER,
    },
    {
      label: t('workflow.label_template_group'),
      value: workflow?.config?.group_alias || (
        <Link to={`/workflow-center/workflows/accept/basic/${workflow?.id}`}>
          {t('workflow.job_node_pending')}
        </Link>
      ),
    },
    {
      label: t('workflow.label_new_template_name'),
      value: (
        <>
          {(Boolean(workflow?.template_info?.name) && (
            <Link
              to={`/workflow-center/workflow-templates/detail/${workflow?.template_info?.id}/config`}
            >
              {workflow?.template_info?.name}
            </Link>
          )) ||
            (workflow?.config && t('workflow.tpl_deleted')) ||
            t('workflow.tpl_config_pending')}
          {workflow?.template_info?.is_modified && workflow?.config && (
            <Button type="text" size="mini" onClick={onDownloadTemplate}>
              {t('workflow.tpl_modified')}
            </Button>
          )}
        </>
      ),
    },
    {
      label: t('workflow.label_project'),
      value: <WhichProject id={workflow?.project_id} />,
    },
    {
      label: t('workflow.label_running_time'),
      value: Boolean(workflow) && <CountTime time={runningTime} isStatic={!isRunning_} />,
    },
    {
      label: t('workflow.label_revision'),
      value: workflow?.template_info?.revision_index
        ? `V${workflow?.template_info?.revision_index}`
        : '-',
    },
    {
      label: t('workflow.label_creator'),
      value: workflow?.creator || '-',
    },
    {
      label: t('workflow.label_batch_update_interval'),
      value: `${workflow?.cron_config && stringifyCron(workflow.cron_config)}`,
      hidden: !workflow?.cron_config,
    },
    // Display workflow global variables
    ...(workflow?.config?.variables || []).map((item) => ({
      label: item.name,
      value: item.value,
      accessMode: item.access_mode,
    })),
  ];

  const { markThem } = useMarkFederatedJobs();

  let jobsWithExeDetails = _mergeWithExecutionDetails(workflow);
  let peerJobsWithExeDetails = _mergeWithExecutionDetails(peerWorkflowQuery.data);
  jobsWithExeDetails = _markJobFlags(jobsWithExeDetails, workflow?.create_job_flags!);
  peerJobsWithExeDetails = _markJobFlags(peerJobsWithExeDetails, workflow?.peer_create_job_flags!);

  markThem(jobsWithExeDetails, peerJobsWithExeDetails);

  const BreadcrumbLinkPaths = useMemo(() => {
    if (params.type === 'model-management') {
      const formattedExtraWorkflow = workflow ? formatExtra(workflow) : ({} as Workflow);
      return [
        {
          label: 'menu.label_model_center_model_training',
          to: '/model-center/model-management',
        },
        {
          label: formattedExtraWorkflow['model_group.name'] || CONSTANTS.EMPTY_PLACEHOLDER,
          to: `/model-center/model-management/model-set/${formattedExtraWorkflow['model.group_id']}`,
        },
        { label: formattedExtraWorkflow.name || CONSTANTS.EMPTY_PLACEHOLDER },
      ];
    }
    if (params.kind_label === 'processed') {
      return [
        {
          label: 'menu.label_datasets',
          to: '/datasets/processed/my',
        },
        {
          label: 'menu.label_datasets_job',
          to: '/datasets/processed/my',
        },
      ];
    }

    return [
      { label: 'menu.label_workflow', to: '/workflow-center/workflows' },
      { label: 'workflow.execution_detail' },
    ];
  }, [params, workflow]);

  const participantIdList = useMemo(() => {
    if (workflow?.project_id && projectList && projectList.length > 0) {
      const currentWorkflowProject = projectList.find((item) => item.id === workflow.project_id);
      if (currentWorkflowProject && currentWorkflowProject.participants) {
        return currentWorkflowProject.participants.map((item) => item.id);
      }
    }
    return [];
  }, [workflow, projectList]);

  const isModelCenterMode =
    params.type === 'model-management' ||
    params.type === 'model-evaluation' ||
    params.type === 'offline-prediction';

  function onEditClick() {
    if (!workflow) {
      return;
    }
    const formattedExtraWorkflow = workflow ? formatExtra(workflow) : ({} as Workflow);

    history.push(
      `/model-center/${params.type}/${
        formattedExtraWorkflow.isReceiver ? 'receiver' : 'sender'
      }/edit/global/${formattedExtraWorkflow.id}/${formattedExtraWorkflow['model.group_id'] || ''}`,
    );
  }
  function onAcceptClick() {
    if (!workflow) {
      return;
    }

    history.push(`/model-center/${params.type}/receiver/edit/global/${workflow.id}`);
  }

  return (
    <SharedPageLayout
      title={<BreadcrumbLink paths={BreadcrumbLinkPaths} />}
      contentWrapByCard={false}
    >
      <Spin loading={detailQuery.isLoading}>
        <>
          <section className={styled.chart_section}>
            <Card className={styled.header_card}>
              <Row
                className={styled.header_row}
                justify="space-between"
                align="center"
                data-forked={isForked}
              >
                <GridRow gap="8">
                  <ClickToCopy text={workflow?.name || ''}>
                    <Tooltip position="top" content={workflow?.name}>
                      <h3 className={styled.name}>{workflow?.name}</h3>
                    </Tooltip>
                  </ClickToCopy>
                  {workflow && <WorkflowStage workflow={workflow} tag />}
                </GridRow>
                {workflow && (
                  <Col flex="200px">
                    <WorkflowActions
                      size="small"
                      workflow={workflow}
                      onSuccess={detailQuery.refetch}
                      onEditClick={isModelCenterMode ? onEditClick : undefined}
                      onAcceptClick={isModelCenterMode ? onAcceptClick : undefined}
                    />
                  </Col>
                )}
              </Row>

              {isForked && originWorkflowQuery.isSuccess && (
                <div className={styled.forked_form}>
                  <IconBranch />
                  {t('workflow.forked_from')}
                  <Link
                    className={styled.origin_workflow_link}
                    to={`/workflow-center/workflows/${originWorkflowQuery.data?.data.id}`}
                  >
                    {originWorkflowQuery.data?.data.name}
                  </Link>
                </div>
              )}
              <VariablePermissionLegend desc={true} prefix="对侧" />

              <PropertyList
                labelWidth={100}
                initialVisibleRows={3}
                cols={3}
                colProportions={[1, 2, 1]}
                properties={workflowProps}
                style={{ marginBottom: '0' }}
              />
            </Card>
          </section>
          <section className={styled.chart_section}>
            {/* Our config */}
            <div className={styled.chart_container}>
              <Row className={styled.chart_header} justify="space-between" align="center">
                <h3
                  className={styled.chart_title}
                  data-note={peerJobsVisible ? t('workflow.federated_note') : ''}
                >
                  {t('workflow.our_config')}
                </h3>

                {isLocalRun && <LocalWorkflowNote />}

                {!peerJobsVisible && !isLocalRun && (
                  <Button icon={<IconEye />} onClick={() => togglePeerJobsVisible(true)}>
                    {t('workflow.btn_see_peer_config')}
                  </Button>
                )}
              </Row>

              {jobsWithExeDetails.length === 0 ? (
                <div className={styled.no_jobs}>
                  <NoResult
                    text={t('workflow.msg_not_config')}
                    CTAText={t('workflow.action_configure')}
                    to={`/workflow-center/workflows/accept/basic/${params.id}`}
                  />
                </div>
              ) : (
                <ReactFlowProvider>
                  <WorkflowJobsCanvas
                    nodeType="execution"
                    workflowConfig={{
                      ...workflow?.config!,
                      job_definitions: jobsWithExeDetails,
                      variables: workflow?.config?.variables || [],
                    }}
                    onJobClick={viewJobDetail}
                    onCanvasClick={hideAllDrawer}
                  />
                  <GlobalConfigDrawer
                    key="self"
                    visible={globalConfigDrawerVisible && !isPeerSide}
                    toggleVisible={toggleGlobalConfigDrawerVisible}
                    jobData={data}
                    workflow={workflow}
                  />
                </ReactFlowProvider>
              )}
            </div>

            {/* Peer config */}
            {peerJobsVisible && (
              <div className={styled.chart_container}>
                <Row className={styled.chart_header} justify="space-between" align="center">
                  <h3
                    className={styled.chart_title}
                    data-note={peerJobsVisible ? t('workflow.federated_note') : ''}
                  >
                    {t('workflow.peer_config')}
                  </h3>

                  <Button icon={<IconEyeInvisible />} onClick={() => togglePeerJobsVisible(false)}>
                    {t('workflow.btn_hide_peer_config')}
                  </Button>
                </Row>

                {peerJobsWithExeDetails.length === 0 ? (
                  <div className={styled.no_jobs}>
                    {peerWorkflowQuery.isFetching ? (
                      <Spin style={{ margin: 'auto' }} />
                    ) : (
                      <NoResult text={t('workflow.msg_peer_not_ready')} />
                    )}
                  </div>
                ) : (
                  <ReactFlowProvider>
                    <WorkflowJobsCanvas
                      nodeType="execution"
                      workflowConfig={{
                        ...peerWorkflowQuery.data?.config!,
                        job_definitions: peerJobsWithExeDetails,
                        variables: peerWorkflow?.config?.variables || [],
                      }}
                      onJobClick={viewPeerJobDetail}
                      onCanvasClick={hideAllDrawer}
                    />
                    <GlobalConfigDrawer
                      key="peer"
                      visible={globalConfigDrawerVisible && isPeerSide}
                      toggleVisible={toggleGlobalConfigDrawerVisible}
                      jobData={data}
                      placement="left"
                      workflow={peerWorkflow}
                      isPeerSide
                    />
                  </ReactFlowProvider>
                )}
              </div>
            )}
          </section>
          <JobExecutionDetailsDrawer
            key="self"
            visible={jobExecutionDetailsDrawerVisible && !isPeerSide}
            toggleVisible={toggleJobExecutionDetailsDrawerVisible}
            jobData={data}
            workflow={workflow}
          />
          {/* Note: Only support one participant now, it will support 2+ participant soon */}
          <JobExecutionDetailsDrawer
            key="peer"
            visible={jobExecutionDetailsDrawerVisible && isPeerSide}
            toggleVisible={toggleJobExecutionDetailsDrawerVisible}
            jobData={data}
            placement="left"
            workflow={peerWorkflow}
            participantId={participantIdList?.[0] ?? 0}
            isPeerSide
          />
        </>
      </Spin>
    </SharedPageLayout>
  );

  function viewJobDetail(jobNode: JobNode) {
    if (jobNode?.type === 'global') {
      setIsPeerSide(false);
      showGlobalConfigDrawer(jobNode);
      return;
    }
    setIsPeerSide(false);
    showJobDetaileDrawer(jobNode);
  }
  function viewPeerJobDetail(jobNode: JobNode) {
    if (jobNode?.type === 'global') {
      setIsPeerSide(true);
      showGlobalConfigDrawer(jobNode);
      return;
    }
    setIsPeerSide(true);
    showJobDetaileDrawer(jobNode);
  }
  function showJobDetaileDrawer(jobNode: JobNode) {
    setData(jobNode.data);
    toggleJobExecutionDetailsDrawerVisible(true);
  }
  function showGlobalConfigDrawer(jobNode: JobNode) {
    setData(jobNode.data);
    toggleGlobalConfigDrawerVisible(true);
  }
  function hideAllDrawer() {
    toggleGlobalConfigDrawerVisible(false);
    toggleJobExecutionDetailsDrawerVisible(false);
  }
  function stringifyCron(cron: string) {
    const { method, weekday, time } = parseCron(cron);
    if (method === 'week') {
      let weekdayString;
      switch (weekday) {
        case 0:
          weekdayString = '星期天';
          break;
        case 1:
          weekdayString = '星期一';
          break;

        case 2:
          weekdayString = '星期二';
          break;

        case 3:
          weekdayString = '星期三';
          break;

        case 4:
          weekdayString = '星期四';
          break;

        case 5:
          weekdayString = '星期五';
          break;

        case 6:
          weekdayString = '星期六';
          break;

        default:
          weekdayString = '未知时间';
      }
      const timeString = time!.format('HH:mm');
      return `${weekdayString} ${timeString}`;
    } else if (method === 'hour') {
      const timeString = time!.format('mm:ss');
      return `每时 ${timeString}`;
    }
    const timeString = time!.format('HH:mm');
    return `每天 ${timeString}`;
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
