import React, { FC } from 'react';
import styled from 'styled-components';
import { Card, Spin, Row, Col } from 'antd';
import { useParams } from 'react-router-dom';
import { useQuery } from 'react-query';
import { getWorkflowDetailById } from 'services/workflow';
import { Job } from 'typings/workflow';
import WorkflowJobsFlowChart from 'components/WorkflowJobsFlowChart';
import { useTranslation } from 'react-i18next';
import { SyncOutlined, BookOutlined } from '@ant-design/icons';
import { xShapeTemplate } from 'services/mocks/v2/workflow_templates/example';
import WhichProject from 'components/WhichProject';
import { fromNow } from 'shared/date';
import WorkflowActions from '../WorkflowActions';
import WorkflowStage from '../WorkflowList/WorkflowStage';
import GridRow from 'components/_base/GridRow';

const ChartSection = styled.section`
  margin-top: 16px;
`;
const Name = styled.h3`
  margin-bottom: 0;
  font-size: 20px;
  line-height: 28px;
`;
const PropsRow = styled.dl`
  display: flex;
  margin-top: 30px;
  padding: 7px 16px;
  background-color: var(--gray1);
`;
const Prop = styled.dd`
  margin-bottom: 0;
  font-size: 13px;
  line-height: 36px;

  &::before {
    content: attr(data-label) '：';
    color: var(--textColorSecondary);
  }
`;
const Header = styled.header`
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

  const { isLoading, data, error } = useQuery(
    ['getWorkflowDetailById', params.id],
    () => getWorkflowDetailById(params.id),
    {
      cacheTime: 1,
    },
  );

  const workflow = data?.data;

  return (
    <Spin spinning={isLoading}>
      <Card>
        <Row justify="space-between" align="middle">
          <GridRow gap="8">
            <Name>{workflow?.name}</Name>
            {workflow && <WorkflowStage data={workflow} tag />}
          </GridRow>
          {workflow && <WorkflowActions workflow={workflow} without={['detail']} />}
        </Row>
        <PropsRow>
          <Col span={8}>
            <Prop data-label={t('workflow.label_template_name')}>
              {workflow?.config?.group_alias}
            </Prop>
          </Col>
          <Col span={8}>
            <Prop data-label={t('workflow.label_project')}>
              <WhichProject id={workflow?.project_id || 0} />
            </Prop>
          </Col>
          <Col span={8}>
            <Prop data-label={t('workflow.label_running_time')}>
              {fromNow(workflow?.start_running_at || 1610238602, true)}
            </Prop>
          </Col>
        </PropsRow>
      </Card>

      <ChartSection>
        <Header>
          <ChartTitle>{t('workflow.our_config')}</ChartTitle>
        </Header>
        <WorkflowJobsFlowChart jobs={workflow?.config?.job_definitions || []} />
      </ChartSection>
    </Spin>
  );
};

export default WorkflowDetail;
