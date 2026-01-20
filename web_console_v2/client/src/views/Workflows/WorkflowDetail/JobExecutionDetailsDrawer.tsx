import ErrorBoundary from 'components/ErrorBoundary';
import React, { ForwardRefRenderFunction, useState } from 'react';
import styled from './JobExecutionDetailsDrawer.module.less';
import { Drawer, Grid, Button, Tag, Tabs } from '@arco-design/web-react';
import { DrawerProps } from '@arco-design/web-react/es/Drawer';
import { IconClose } from '@arco-design/web-react/icon';
import { useQuery } from 'react-query';
import { NodeData, ChartNodeStatus, JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import { executionStatusText } from 'components/WorkflowJobsCanvas/JobNodes/shared';
import { convertExecutionStateToStatus } from 'components/WorkflowJobsCanvas/helpers';
import { VariablePermissionLegend } from 'components/VariblePermission';
import CodeEditorButton from 'components/ModelCodesEditorButton';
import AlgorithmDrawer from 'components/AlgorithmDrawer';
import CodeEditor from 'components/CodeEditor';
import CountTime from 'components/CountTime';
import GridRow from 'components/_base/GridRow';
import PropertyList from 'components/PropertyList';
import { useTranslation } from 'react-i18next';
import { formatTimestamp } from 'shared/date';
import { formatJSONValue } from 'shared/helpers';
import JobExecutionLogs from './JobExecutionLogs';
import JobExecutionMetrics from './JobExecutionMetrics';
import JobExecutionPods from './JobExecutionPods';
import { fetchJobById } from 'services/workflow';
import { WorkflowExecutionDetails } from 'typings/workflow';
import { VariableComponent, VariableWidgetSchema, VariableAccessMode } from 'typings/variable';
import { JobState } from 'typings/job';
import JobKibanaMetrics from './JobKibanaMetrics';
import dayjs from 'dayjs';

const Row = Grid.Row;

interface Props extends DrawerProps {
  isPeerSide?: boolean;
  jobData?: NodeData;
  workflow?: WorkflowExecutionDetails;
  toggleVisible?: Function;
  participantId?: ID;
}

export type JobExecutionDetailsExposedRef = {};
export const JobExecutionDetailsContext = React.createContext({
  job: (undefined as unknown) as JobNodeRawData,
  workflow: undefined as WorkflowExecutionDetails | undefined,
  isPeerSide: undefined as boolean | undefined,
  participantId: undefined as ID | undefined,
});

enum JobDetailTabs {
  Basic = 'basic',
  Kibana = 'kibana',
  Yaml = 'yaml',
}

const tagColors = {
  [ChartNodeStatus.Pending]: 'default',
  [ChartNodeStatus.Processing]: 'blue',
  [ChartNodeStatus.Validating]: 'blue',
  [ChartNodeStatus.Warning]: 'orange',
  [ChartNodeStatus.Success]: 'green',
  [ChartNodeStatus.Error]: 'red',
};

const JobExecutionDetailsDrawer: ForwardRefRenderFunction<JobExecutionDetailsExposedRef, Props> = ({
  jobData,
  workflow,
  isPeerSide = false,
  toggleVisible,
  participantId,
  ...props
}) => {
  const { t } = useTranslation();
  const [currTab, setTab] = useState(JobDetailTabs.Basic);
  const jobQuery = useQuery(
    ['fetchJobById', jobData?.raw.id],
    () => fetchJobById(jobData?.raw.id),
    {
      enabled: Boolean(jobData?.raw.id) && props.visible,
    },
  );

  // in peerSide, jobData.raw.id is null, jobQuery is idle, so use jobData?.raw to help <JobExecutionPods/> show Pod table list
  const data = isPeerSide ? (jobData?.raw as any) : jobQuery.data?.data;

  if (!jobData || !jobData.raw) {
    return null;
  }
  const job = jobData.raw;
  const yaml = data ? data.snapshot : '';
  const displayedProps: Array<{
    label: string;
    value: any;
    hidden?: boolean;
    accessMode?: VariableAccessMode;
  }> = [
    {
      label: 'K8s Job name',
      value: job.k8sName,
    },
    {
      label: '任务类型',
      value: job.job_type,
    },
    {
      label: '任务创建时间',
      value: formatTimestamp(job.created_at || 0),
    },
    {
      label: '运行时长',
      value: renderRuntime(),
    },
  ];

  job.variables.forEach((item) => {
    const widgetSchemaString = (item.widget_schema as unknown) as string;
    let configValue = item.value || <span style={{ color: 'var(--textColorDisabled)' }}>N/A</span>;
    try {
      const parsedWidgetSchema = JSON.parse(widgetSchemaString) as VariableWidgetSchema;
      // Set the value of the list item "code_tar" to a button to open the editor in read-only mode
      if (parsedWidgetSchema.component === VariableComponent.Code) {
        configValue = (
          <CodeEditorButton
            value={JSON.parse(item.value)}
            disabled={true}
            buttonText="查看全部代码"
            buttonType="text"
            buttonIcon={null}
            buttonStyle={{ padding: 0 }}
          />
        );
      }

      if (parsedWidgetSchema.component === VariableComponent.AlgorithmSelect) {
        const { algorithmProjectId, algorithmId, config = [] } = JSON.parse(item.value);
        configValue = (
          <AlgorithmDrawer.Button
            algorithmProjectId={algorithmProjectId}
            algorithmId={algorithmId}
            parameterVariables={config}
          >
            <span className={styled.check_text}>{t('check')}</span>
          </AlgorithmDrawer.Button>
        );
      }
    } catch (error) {}

    displayedProps.push({
      label: item.name,
      value: configValue,
      accessMode: item.access_mode,
    });
  });

  const jobStatus = convertExecutionStateToStatus(job.state!);
  return (
    <ErrorBoundary>
      <JobExecutionDetailsContext.Provider value={{ job, workflow, isPeerSide, participantId }}>
        <Drawer
          className={styled.container}
          mask={false}
          width="980px"
          onCancel={closeDrawer}
          headerStyle={{ display: 'none' }}
          wrapClassName="#app-content"
          footer={null}
          {...props}
        >
          <Row className={styled.drawer_header} align="center" justify="space-between">
            <Row align="center">
              <h3 className={styled.drawer_title}>
                {job.name}
                <small className={styled.id_text}>ID: {job.id}</small>
              </h3>

              {isPeerSide ? (
                <Tag color="orange" bordered>
                  {t('workflow.peer_config')}
                </Tag>
              ) : (
                <Tag color="cyan" bordered>
                  {t('workflow.our_config')}
                </Tag>
              )}

              <Tag style={{ marginLeft: '5px' }} color={tagColors[jobStatus]} bordered>
                {executionStatusText[jobStatus]}
              </Tag>
            </Row>
            <GridRow gap="10">
              <Button size="small" icon={<IconClose />} onClick={closeDrawer} />
            </GridRow>
          </Row>

          <div className={styled.cover_header_shadow_if_not_sticky} />

          <Tabs defaultActiveTab={currTab} onChange={onTabChange as any}>
            <Tabs.TabPane title={t('workflow.label_job_basics')} key={JobDetailTabs.Basic} />
            <Tabs.TabPane title={t('workflow.label_job_yaml_detail')} key={JobDetailTabs.Yaml} />
            <Tabs.TabPane
              title={t('workflow.label_job_kibana_metrics')}
              key={JobDetailTabs.Kibana}
            />
          </Tabs>

          <div className={styled.tab_panel} data-visible={currTab === JobDetailTabs.Basic}>
            <VariablePermissionLegend desc={true} prefix="对侧" />
            <PropertyList
              initialVisibleRows={3}
              cols={2}
              properties={displayedProps}
              labelWidth={90}
            />
            <JobExecutionMetrics
              job={job}
              workflow={workflow}
              isPeerSide={isPeerSide}
              visible={props.visible}
              participantId={participantId}
            />
            <JobExecutionLogs
              isPeerSide={isPeerSide}
              job={job}
              workflow={workflow}
              enabled={Boolean(props.visible)}
              participantId={participantId}
            />
            <JobExecutionPods job={data} isPeerSide={isPeerSide} loading={jobQuery.isFetching} />
          </div>

          <div className={styled.tab_panel} data-visible={currTab === JobDetailTabs.Kibana}>
            <JobKibanaMetrics job={job} isPeerSide={isPeerSide} />
          </div>

          <div className={styled.tab_panel} data-visible={currTab === JobDetailTabs.Yaml}>
            <div className={styled.code_editor_container}>
              <CodeEditor
                value={yaml ? formatJSONValue(yaml) : ''}
                language="json"
                isReadOnly={true}
              />
            </div>
          </div>
        </Drawer>
      </JobExecutionDetailsContext.Provider>
    </ErrorBoundary>
  );

  function closeDrawer() {
    toggleVisible && toggleVisible(false);
  }
  function onTabChange(activeTab: JobDetailTabs) {
    setTab(activeTab);
  }

  function renderRuntime() {
    let runningTime: number = 0;
    const isRunning_ = job.state === JobState.STARTED;
    const isStopped_ = [JobState.STOPPED, JobState.COMPLETED, JobState.FAILED].includes(job.state);
    const startedAt = job.start_at || job.updated_at;
    if (isStopped_) {
      runningTime = job.completed_at || job.updated_at - startedAt!;
    } else if (isRunning_) {
      runningTime = dayjs().unix() - startedAt!;
    }
    return <CountTime time={runningTime} isStatic={!isRunning_} isResetOnChange={true} />;
  }
};

export default JobExecutionDetailsDrawer;
