import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import React, { ForwardRefRenderFunction, useState } from 'react';
import styled from 'styled-components';
import { Drawer, Row, Button, Tag, Tabs } from 'antd';
import { DrawerProps } from 'antd/lib/drawer';
import { NodeData, ChartNodeStatus, JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import { useTranslation } from 'react-i18next';
import { Close } from 'components/IconPark';
import GridRow from 'components/_base/GridRow';
import { formatTimestamp } from 'shared/date';
import PropertyList from 'components/PropertyList';
import JobExecutionLogs from './JobExecutionLogs';
import JobExecutionMetrics from './JobExecutionMetrics';
import JobExecutionPods from './JobExecutionPods';
import { executionStatusText } from 'components/WorkflowJobsCanvas/JobNodes/shared';
import { convertExecutionStateToStatus } from 'components/WorkflowJobsCanvas/helpers';
import { WorkflowExecutionDetails } from 'typings/workflow';
import defaultTheme from 'styles/_theme';
import JobKibanaMetrics from './JobKibanaMetrics/index.tsx';

const Container = styled(Drawer)`
  top: 60px;

  .ant-drawer-body {
    padding-top: 0;
    padding-bottom: 200px;
  }
`;
const DrawerHeader = styled(Row)`
  position: sticky;
  z-index: 2;
  top: 0;
  margin: 0 -24px 0;
  padding: 20px 16px 20px 24px;
  background-color: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
`;
const CoverHeaderShadowIfNotSticky = styled.div`
  position: sticky;
  bottom: 0;
  z-index: 5;
  top: 50px;
  margin: 0 -24px 0;
  height: 12px;
  background-color: #fff;
`;
const DrawerTitle = styled.h3`
  position: relative;
  margin-bottom: 0;
  margin-right: 10px;
`;
const ID = styled.small`
  margin-left: 10px;
  color: var(--textColorSecondary);
`;
const TabPanel = styled.div`
  display: none;

  &[data-visible='true'] {
    display: block;
  }
`;

interface Props extends DrawerProps {
  isPeerSide?: boolean;
  jobData?: NodeData;
  workflow?: WorkflowExecutionDetails;
  toggleVisible?: Function;
}

export type JobExecutionDetailsExposedRef = {};
export const JobExecutionDetailsContext = React.createContext({
  job: (undefined as unknown) as JobNodeRawData,
  workflow: undefined as WorkflowExecutionDetails | undefined,
  isPeerSide: undefined as boolean | undefined,
});

enum JobDetailTabs {
  Basic = 'basic',
  Kibana = 'kibana',
}

const tagColors = {
  [ChartNodeStatus.Pending]: 'default',
  [ChartNodeStatus.Processing]: 'processing',
  [ChartNodeStatus.Warning]: 'warning',
  [ChartNodeStatus.Success]: 'success',
  [ChartNodeStatus.Error]: 'error',
};

const JobExecutionDetailsDrawer: ForwardRefRenderFunction<JobExecutionDetailsExposedRef, Props> = ({
  jobData,
  workflow,
  isPeerSide = false,
  toggleVisible,
  ...props
}) => {
  const { t } = useTranslation();
  const [currTab, setTab] = useState(JobDetailTabs.Basic);

  if (!jobData || !jobData.raw) {
    return null;
  }

  const job = jobData.raw;

  const displayedProps = [
    {
      label: 'K8s Job name',
      value: job.k8sName,
    },
    {
      label: t('workflow.label_job_type'),
      value: job.job_type,
    },
    {
      label: t('workflow.label_job_created'),
      value: formatTimestamp(job.created_at || 0),
    },
  ];

  job.variables.forEach((item) => {
    displayedProps.push({
      label: item.name,
      value: item.value || <span style={{ color: defaultTheme.textColorDisabled }}>N/A</span>,
    });
  });

  const jobStatus = convertExecutionStateToStatus(job.state!);

  return (
    <ErrorBoundary>
      <JobExecutionDetailsContext.Provider value={{ job, workflow, isPeerSide }}>
        <Container
          getContainer="#app-content"
          mask={false}
          width="980px"
          onClose={closeDrawer}
          headerStyle={{ display: 'none' }}
          {...props}
        >
          <DrawerHeader align="middle" justify="space-between">
            <Row align="middle">
              <DrawerTitle>
                {job.name}
                <ID>ID: {job.id}</ID>
              </DrawerTitle>

              {isPeerSide ? (
                <Tag color="orange">{t('workflow.peer_config')}</Tag>
              ) : (
                <Tag color="cyan">{t('workflow.our_config')}</Tag>
              )}

              <Tag color={tagColors[jobStatus]}>{executionStatusText[jobStatus]}</Tag>
            </Row>
            <GridRow gap="10">
              <Button size="small" icon={<Close />} onClick={closeDrawer} />
            </GridRow>
          </DrawerHeader>

          <CoverHeaderShadowIfNotSticky />

          <Tabs defaultActiveKey={currTab} onChange={onTabChange as any}>
            <Tabs.TabPane tab={t('workflow.label_job_basics')} key={JobDetailTabs.Basic} />
            <Tabs.TabPane tab={t('workflow.label_job_kibana_metrics')} key={JobDetailTabs.Kibana} />
          </Tabs>

          <TabPanel data-visible={currTab === JobDetailTabs.Basic}>
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
            />

            <JobExecutionLogs
              isPeerSide={isPeerSide}
              job={job}
              workflow={workflow}
              enabled={Boolean(props.visible)}
            />

            <JobExecutionPods job={job} isPeerSide={isPeerSide} />
          </TabPanel>

          <TabPanel data-visible={currTab === JobDetailTabs.Kibana}>
            <JobKibanaMetrics job={job} isPeerSide={isPeerSide} />
          </TabPanel>
        </Container>
      </JobExecutionDetailsContext.Provider>
    </ErrorBoundary>
  );

  function closeDrawer() {
    toggleVisible && toggleVisible(false);
  }
  function onTabChange(activeTab: JobDetailTabs) {
    setTab(activeTab);
  }
};

export default JobExecutionDetailsDrawer;
