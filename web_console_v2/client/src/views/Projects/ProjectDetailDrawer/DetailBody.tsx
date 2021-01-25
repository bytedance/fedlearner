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

  const workflowQuery = useQuery(['fetchWorkflowList', project.id], () =>
    fetchWorkflowList({ project: project.id }),
  );

  const participant = project.config.participants[0];
  const properties = [
    {
      label: t('project.participant_name'),
      value: project.name,
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
  ];
  return (
    <ErrorBoundary>
      <PropertyList properties={properties} cols={2} labelWidth={105} />

      <Tabs defaultActiveKey="workflow">
        <Tabs.TabPane tab={t('project.workflow')} key="workflow">
          <Table
            loading={workflowQuery.isLoading}
            dataSource={workflowQuery.data?.data || []}
            columns={getWorkflowTableColumns({ withoutActions: true })}
          />
        </Tabs.TabPane>
        <Tabs.TabPane tab={t('project.mix_dataset')} key="dataset">
          Dataset table here
        </Tabs.TabPane>
        <Tabs.TabPane tab={t('project.model')} key="model">
          Model table here
        </Tabs.TabPane>
        <Tabs.TabPane tab="API" key="api">
          API table here
        </Tabs.TabPane>
      </Tabs>
    </ErrorBoundary>
  );
}

export default DetailBody;
