import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import React, { ForwardRefRenderFunction } from 'react';
import styled from 'styled-components';
import { Drawer, Row, Button, Tag } from 'antd';
import { DrawerProps } from 'antd/lib/drawer';
import { NodeData, ChartNodeStatus } from 'components/WorkflowJobsFlowChart/types';
import { useTranslation } from 'react-i18next';
import { Close } from 'components/IconPark';
import GridRow from 'components/_base/GridRow';
import { formatTimestamp } from 'shared/date';
import PropertyList from 'components/PropertyList';
import JobExecutionLogs from './JobExecutionLogs';
import JobExecutionMetrics from './JobExecutionMetrics';
import JobExecutionPods from './JobExecutionPODs';
import { jobExecutionStatusText } from 'components/WorkflowJobsFlowChart/WorkflowJobNode';
import { convertExecutionStateToStatus } from 'components/WorkflowJobsFlowChart/helpers';
import { WorkflowExecutionDetails } from 'typings/workflow';
import defaultTheme from 'styles/_theme';

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

interface Props extends DrawerProps {
  isPeerSide: boolean;
  jobData?: NodeData;
  workflow?: WorkflowExecutionDetails;
  toggleVisible?: Function;
}
export type JobExecutionDetailsExposedRef = {};

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
  isPeerSide,
  toggleVisible,
  ...props
}) => {
  const { t } = useTranslation();

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
      <Container
        getContainer="#app-content"
        mask={false}
        width="880px"
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

            <Tag color={tagColors[jobStatus]}>{jobExecutionStatusText[jobStatus]}</Tag>
          </Row>
          <GridRow gap="10">
            <Button size="small" icon={<Close />} onClick={closeDrawer} />
          </GridRow>
        </DrawerHeader>

        <CoverHeaderShadowIfNotSticky />

        <PropertyList initialVisibleRows={3} cols={2} properties={displayedProps} labelWidth={90} />

        {!isPeerSide && <JobExecutionMetrics job={job} visible={props.visible} />}

        <JobExecutionLogs
          isPeerSide
          job={job}
          workflow={workflow}
          enabled={Boolean(props.visible)}
        />

        <JobExecutionPods job={job} isPeerSide={isPeerSide} />
      </Container>
    </ErrorBoundary>
  );

  function closeDrawer() {
    toggleVisible && toggleVisible(false);
  }
};

export default JobExecutionDetailsDrawer;
