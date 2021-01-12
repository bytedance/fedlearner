import React, { useState } from 'react';
import styled from 'styled-components';
import { Row, Col, Button, Form, Input, Select, Table, message } from 'antd';
import { useList } from 'react-use';
import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { fetchWorkflowList } from 'services/workflow';
import i18n from 'i18n';
import { formatTimestamp } from 'shared/date';
import { useTranslation } from 'react-i18next';
import ListPageLayout from 'components/ListPageLayout';
import { Workflow } from 'typings/workflow';
import WorkflowStage from './WorkflowStage';
import { isStopped, isRunning, isPendingAccpet, isReadyToRun } from 'shared/workflow';
import ProjectCell from 'components/ProjectCell';

const FilterItem = styled(Form.Item)`
  > .ant-form-item-control {
    width: 227px;
  }
`;

const tableColumns = [
  {
    title: i18n.t('workflow.name'),
    dataIndex: 'name',
    key: 'name',
    render: (name: string, record: Workflow) => {
      if (isPendingAccpet(record)) {
        return name;
      }
      return (
        <Link to={`/workflows/${record.id}`} rel="nopener">
          {name}
        </Link>
      );
    },
  },
  {
    title: i18n.t('workflow.col_status'),
    dataIndex: 'state',
    name: 'state',
    render: (_: string, record: Workflow) => <WorkflowStage data={record} />,
  },
  {
    title: i18n.t('workflow.col_project'),
    dataIndex: 'project_id',
    name: 'project_id',
    width: 150,
    render: (project_id: number) => <ProjectCell id={project_id} />,
  },
  {
    title: i18n.t('workflow.col_date'),
    dataIndex: 'created_at',
    name: 'created_at',
    render: (date: number) => <div>{formatTimestamp(date)}</div>,
  },
  {
    title: i18n.t('workflow.col_actions'),
    dataIndex: 'created_at',
    name: 'created_at',
    render: (_: any, record: Workflow) => (
      <div>
        {isPendingAccpet(record) && (
          <Link to={`/workflows/accept/${record.id}/basic`}>
            <Button size="small" type="link">
              {i18n.t('workflow.action_configure')}
            </Button>
          </Link>
        )}
        {isReadyToRun(record) && (
          <Button size="small" type="link">
            {i18n.t('workflow.action_run')}
          </Button>
        )}
        {isRunning(record) && (
          <Button size="small" type="link">
            {i18n.t('workflow.action_stop_running')}
          </Button>
        )}
        {isStopped(record) && (
          <Button size="small" type="link">
            {i18n.t('workflow.action_re_run')}
          </Button>
        )}
        <Button size="small" type="link">
          {i18n.t('workflow.action_duplicate')}
        </Button>
        <Button size="small" type="link">
          {i18n.t('workflow.action_detail')}
        </Button>
      </div>
    ),
  },
];

type QueryParams = {
  project?: string;
  keyword?: string;
};

function WorkflowsTable() {
  const { t } = useTranslation();
  const [form] = Form.useForm<QueryParams>();
  const [projectList] = useList([{ value: '', label: t('all') }]);
  const [params, setParams] = useState<QueryParams>({ project: '', keyword: '' });

  const { isLoading, isError, data: res, error } = useQuery(
    ['fetchWorkflowList', params.project, params.keyword],
    () => fetchWorkflowList(params),
  );

  if (isError && error) {
    message.error((error as Error).message);
  }

  function handleSearch(values: QueryParams) {
    setParams(values);
  }

  return (
    <ListPageLayout title={t('term.workflow')}>
      <Row gutter={16} justify="space-between">
        <Col>
          <Link to="/workflows/initiate/basic">
            <Button type="primary">{t('workflow.create_workflow')}</Button>
          </Link>
        </Col>
        <Col>
          <Form initialValues={{ ...params }} layout="inline" form={form} onFinish={handleSearch}>
            <FilterItem name="project" label={t('term.project')}>
              <Select onChange={form.submit}>
                {projectList.map((item) => (
                  <Select.Option key={item.value} value={item.value}>
                    {item.label}
                  </Select.Option>
                ))}
              </Select>
            </FilterItem>
            <FilterItem name="keyword">
              <Input.Search
                placeholder={t('workflow.placeholder_name_searchbox')}
                onPressEnter={form.submit}
              />
            </FilterItem>
          </Form>
        </Col>
      </Row>

      <Table loading={isLoading} dataSource={res?.data.data || []} columns={tableColumns} />
    </ListPageLayout>
  );
}

export default WorkflowsTable;
