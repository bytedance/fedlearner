import React, { ReactElement } from 'react';
import { Tabs, Table } from 'antd';
import { useTranslation } from 'react-i18next';
import { Project } from 'typings/project';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import PropertyList from 'components/PropertyList';
import { useQuery } from 'react-query';
import { fetchWorkflowList } from 'services/workflow';
import { getWorkflowTableColumns } from 'views/Workflows/WorkflowList';

interface DetailBodyProps {
  project: Project;
}

function DetailBody({ project }: DetailBodyProps): ReactElement {
  const { t } = useTranslation();

  const workflowsQuery = useQuery(['fetchWorkflowList', project.id], () =>
    fetchWorkflowList({ project: project.id }),
  );

  const participant = project.config.participants[0];
  const properties = [
    {
      label: t('project.participant_name'),
      value: participant.name || '-',
    },
    {
      label: t('project.participant_domain'),
      value: participant.domain_name,
    },
    {
      label: t('project.participant_url'),
      value: participant.url,
    },

    {
      label: t('project.remarks'),
      value: project.comment || '-',
    },
    ...project.config.variables.map((item) => ({ label: item.name, value: item.value })),
  ];
  return (
    <ErrorBoundary>
      <PropertyList initialVisibleRows={3} properties={properties} cols={2} labelWidth={105} />

      <Tabs defaultActiveKey="workflow">
        <Tabs.TabPane tab={t('project.workflow')} key="workflow">
          <Table
            loading={workflowsQuery.isLoading}
            dataSource={workflowsQuery.data?.data || []}
            columns={getWorkflowTableColumns({ withoutActions: true })}
          />
        </Tabs.TabPane>
        <Tabs.TabPane tab={t('project.mix_dataset')} key="dataset">
          <Table />
        </Tabs.TabPane>
        <Tabs.TabPane tab={t('project.model')} key="model">
          <Table />
        </Tabs.TabPane>
        <Tabs.TabPane tab="API" key="api">
          <Table />
        </Tabs.TabPane>
      </Tabs>
    </ErrorBoundary>
  );
}

export default DetailBody;
