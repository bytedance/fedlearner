import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { Card, Spin, Row } from 'antd';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { getWorkflowDetailById } from 'services/workflow';
import WorkflowJobsFlowChart from 'components/WorkflowJobsFlowChart';
import { useTranslation } from 'react-i18next';
import WhichProject from 'components/WhichProject';
import { fromNow } from 'shared/date';
import WorkflowActions from '../WorkflowActions';
import WorkflowStage from '../WorkflowList/WorkflowStage';
import GridRow from 'components/_base/GridRow';
import BreadcrumbLink from 'components/BreadcrumbLink';
import JobExecutionDetailsDrawer from './JobExecutionDetailsDrawer';
import { useToggle } from 'react-use';
import { JobNode, JobNodeData } from 'components/WorkflowJobsFlowChart/helpers';
import PropertyList from 'components/PropertyList';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  height: var(--contentHeight);
`;
const ChartSection = styled.section`
  margin-top: 16px;
  flex: 1;
`;
const HeaderRow = styled(Row)`
  margin-bottom: 30px;
`;
const Name = styled.h3`
  margin-bottom: 0;
  font-size: 20px;
  line-height: 28px;
`;
const ChartHeader = styled.header`
  padding: 13px 20px;
  font-size: 14px;
  line-height: 22px;
  background-color: white;
`;
const ChartTitle = styled.h3`
  margin-bottom: 0;
`;

const WorkflowDetail: FC = () => {
  const params = useParams<{ id: string }>();
  const { t } = useTranslation();
  const [drawerVisible, toggleDrawerVisible] = useToggle(false);
  const [isPeerSide, setIsPeerSide] = useState(false);
  const [data, setData] = useState<JobNodeData>();

  const detailQuery = useQuery(
    ['getWorkflowDetailById', params.id],
    () => getWorkflowDetailById(params.id),
    {
      cacheTime: 1,
    },
  );

  const workflow = detailQuery.data?.data;
  const jobDefs = workflow?.config?.job_definitions || [];
  const jobsWithExecutionDetails = jobDefs.map((item) => {
    return Object.assign(
      item,
      workflow?.jobs.find((j) => j.name === item.name),
    );
  });

  return (
    <Spin spinning={detailQuery.isLoading}>
      <Container>
        <BreadcrumbLink
          paths={[
            { label: 'menu.label_workflow', to: '/workflows' },
            { label: 'workflow.execution_detail' },
          ]}
        />
        <Card>
          <HeaderRow justify="space-between" align="middle">
            <GridRow gap="8">
              <Name>{workflow?.name}</Name>
              {workflow && <WorkflowStage workflow={workflow} tag />}
            </GridRow>
            {workflow && <WorkflowActions workflow={workflow} without={['detail']} />}
          </HeaderRow>

          <PropertyList
            cols={3}
            properties={[
              {
                label: t('workflow.label_template_name'),
                value: workflow?.config?.group_alias || (
                  <Link to={`/workflows/accept/basic/${workflow?.id}`}>
                    {t('workflow.job_node_pending')}
                  </Link>
                ),
              },
              {
                label: t('workflow.label_project'),
                value: <WhichProject id={workflow?.project_id || 0} />,
              },
              {
                label: t('workflow.label_running_time'),
                value: fromNow(workflow?.start_running_at || 0, true),
              },
            ]}
          />
        </Card>

        <ChartSection>
          <ChartHeader>
            <ChartTitle>{t('workflow.our_config')}</ChartTitle>
          </ChartHeader>

          <WorkflowJobsFlowChart
            type="execution"
            jobs={jobsWithExecutionDetails}
            onJobClick={viewJobDetail}
          />
        </ChartSection>

        <JobExecutionDetailsDrawer
          visible={drawerVisible}
          toggleVisible={toggleDrawerVisible}
          data={data}
          isPeerSide={isPeerSide}
        />
      </Container>
    </Spin>
  );

  function viewJobDetail(jobNode: JobNode) {
    setData(jobNode.data);

    toggleDrawerVisible(true);
  }
};

export default WorkflowDetail;
