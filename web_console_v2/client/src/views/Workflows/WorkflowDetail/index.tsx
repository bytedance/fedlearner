import React, { FC } from 'react';
import styled from 'styled-components';
import { Card, Spin, Row, Button, Col } from 'antd';
import { useParams } from 'react-router-dom';
import { useQuery } from 'react-query';
import { getWorkflowDetailById } from 'services/workflow';
import { Job } from 'typings/workflow';
import WorkflowJobsFlowChart from 'components/WorkflowJobsFlowChart';
import { isRunning, isReadyToRun } from 'shared/workflow';
import GridRow from 'components/_base/GridRow';
import { useTranslation } from 'react-i18next';
import { CopyOutlined, SyncOutlined, BookOutlined } from '@ant-design/icons';
import { xShapeTemplate } from 'services/mocks/v2/workflow_templates/example';
import ProjectCell from 'components/ProjectCell';
import { fromNow } from 'shared/date';

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
          <div>
            <Name>{workflow?.name}</Name>
          </div>
          {workflow && (
            <GridRow gap="8">
              {isReadyToRun(workflow) && <Button size="small">{t('workflow.action_run')}</Button>}
              {isRunning(workflow) && (
                <Button size="small">{t('workflow.action_stop_running')}</Button>
              )}
              <Button size="small" icon={<BookOutlined />}>
                {t('workflow.btn_show_report')}
              </Button>
              <Button size="small" icon={<SyncOutlined />}>
                {t('workflow.action_re_run')}
              </Button>
              <Button size="small" icon={<CopyOutlined />}>
                {t('workflow.action_fork')}
              </Button>
            </GridRow>
          )}
        </Row>
        <PropsRow>
          <Col span={8}>
            <Prop data-label={t('workflow.label_template_name')}>
              {workflow?.config?.group_alias}
            </Prop>
          </Col>
          <Col span={8}>
            <Prop data-label={t('workflow.label_project')}>
              <ProjectCell id={workflow?.project_id || 0} />
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
