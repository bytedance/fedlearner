import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import React, { ForwardRefRenderFunction } from 'react';
import styled from 'styled-components';
import { Drawer, Row, Col, Button, Tag } from 'antd';
import { DrawerProps } from 'antd/lib/drawer';
import { JobNodeData, JobNodeStatus } from 'components/WorkflowJobsFlowChart/helpers';
import { useTranslation } from 'react-i18next';
import { Close } from 'components/IconPark';
import GridRow from 'components/_base/GridRow';
import { formatTimestamp } from 'shared/date';
import PropertyList from 'components/PropertyList';
import JobExecutionLogs from './JobExecutionLogs';
import JobExecutionMetrics from './JobExecutionMetrics';
import JobExecutionPODs from './JobExecutionPODs';
import { jobExecutionStatusText } from 'components/WorkflowJobsFlowChart/WorkflowJobNode';
import { convertExecutionStateToStatus } from 'components/WorkflowJobsFlowChart/helpers';

const Container = styled(Drawer)`
  top: 60px;

  .ant-drawer-body {
    padding-top: 0;
    padding-bottom: 200px;
  }
`;
const DrawerHeader = styled(Row)`
  margin: 0 -24px 0;
  padding: 20px 16px 20px 24px;
`;
const DrawerTitle = styled.h3`
  margin-bottom: 0;
  margin-right: 10px;
`;

interface Props extends DrawerProps {
  isPeerSide: boolean;
  data?: JobNodeData;
  toggleVisible?: Function;
}
export type JobExecutionDetailsExposedRef = {};

const tagColors = {
  [JobNodeStatus.Pending]: 'default',
  [JobNodeStatus.Processing]: 'processing',
  [JobNodeStatus.Warning]: 'warning',
  [JobNodeStatus.Success]: 'success',
  [JobNodeStatus.Error]: 'error',
};

const JobExecutionDetailsDrawer: ForwardRefRenderFunction<JobExecutionDetailsExposedRef, Props> = ({
  data,
  isPeerSide,
  toggleVisible,
  ...props
}) => {
  const { t } = useTranslation();

  if (!data || !data.raw) {
    return null;
  }

  const job = data.raw;

  const displayedProps = [
    {
      label: 'Job ID',
      value: job.id,
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
            <DrawerTitle>{data.raw.name}</DrawerTitle>

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

        <PropertyList cols={2} properties={displayedProps} labelWidth={90} />

        <JobExecutionMetrics />
        <JobExecutionLogs />
        <JobExecutionPODs pods={job.pods || []} />
      </Container>
    </ErrorBoundary>
  );

  function closeDrawer() {
    toggleVisible && toggleVisible(false);
  }
};

export default JobExecutionDetailsDrawer;
