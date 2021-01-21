import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { Row, Col, Button, Form, Input, Select, Table, message, Spin } from 'antd';
import { useList } from 'react-use';
import { Link, useHistory } from 'react-router-dom';
import { useQuery } from 'react-query';
import { fetchWorkflowList } from 'services/workflow';
import i18n from 'i18n';
import { formatTimestamp } from 'shared/date';
import { useTranslation } from 'react-i18next';
import ListPageLayout from 'components/ListPageLayout';
import { Workflow } from 'typings/workflow';
import WorkflowStage from './WorkflowStage';
import WorkflowActions from '../WorkflowActions';
import WhichProject from 'components/WhichProject';
import NoResult from 'components/NoResult';
import { useRecoilQuery } from 'hooks/recoil';
import { projectListQuery } from 'stores/projects';

const FilterItem = styled(Form.Item)`
  > .ant-form-item-control {
    width: 227px;
  }
`;
const ListContainer = styled.div`
  display: flex;
  flex: 1;
  width: 100%;
`;

export const getTableColumns = (
  options: { onSuccess?: Function; withoutActions?: boolean } = {},
) => {
  const ret = [
    {
      title: i18n.t('workflow.name'),
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Workflow) => {
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
      render: (_: string, record: Workflow) => <WorkflowStage workflow={record} />,
    },
    {
      title: i18n.t('workflow.col_project'),
      dataIndex: 'project_id',
      name: 'project_id',
      width: 150,
      render: (project_id: number) => <WhichProject id={project_id} />,
    },
    {
      title: i18n.t('workflow.col_date'),
      dataIndex: 'created_at',
      name: 'created_at',
      render: (date: number) => <div>{formatTimestamp(date)}</div>,
    },
  ];
  if (!options.withoutActions) {
    ret.push({
      title: i18n.t('workflow.col_actions'),
      dataIndex: 'created_at',
      name: 'created_at',
      render: (_: any, record: Workflow) => (
        <WorkflowActions
          onSuccess={options.onSuccess}
          workflow={record}
          type="link"
          without={['report']}
        />
      ),
    });
  }

  return ret;
};

type QueryParams = {
  project?: string;
  keyword?: string;
};

const WorkflowList: FC = () => {
  const { t } = useTranslation();
  const [form] = Form.useForm<QueryParams>();
  const history = useHistory();
  const [params, setParams] = useState<QueryParams>({ keyword: '' });

  const projectsQuery = useRecoilQuery(projectListQuery);

  const { isLoading, isError, data: res, error, refetch } = useQuery(
    ['fetchWorkflowList', params.project, params.keyword],
    () => fetchWorkflowList(params),
  );

  if (isError && error) {
    message.error((error as Error).message);
  }

  const isEmpty = !res?.data.length;

  return (
    <Spin spinning={isLoading}>
      <ListPageLayout title={t('menu.label_workflow')}>
        <Row gutter={16} justify="space-between" align="middle">
          <Col>
            <Button size="large" type="primary" onClick={goCreate}>
              {t('workflow.create_workflow')}
            </Button>
          </Col>
          <Col>
            <Form initialValues={{ ...params }} layout="inline" form={form} onFinish={onSearch}>
              <FilterItem name="project" label={t('term.project')}>
                <Select
                  onChange={form.submit}
                  onClear={form.submit}
                  loading={projectsQuery.isLoading}
                  disabled={!!projectsQuery.error}
                  allowClear
                  placeholder={t('all')}
                >
                  {projectsQuery.data?.map((item) => (
                    <Select.Option key={item.id} value={item.id}>
                      {item.name}
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

        <ListContainer>
          {isEmpty ? (
            <NoResult text={t('workflow.no_result')} to="/workflows/initiate/basic" />
          ) : (
            <Table dataSource={res?.data || []} columns={getTableColumns({ onSuccess })} />
          )}
        </ListContainer>
      </ListPageLayout>
    </Spin>
  );

  function onSearch(values: QueryParams) {
    setParams(values);
  }
  function onSuccess() {
    refetch();
  }
  function goCreate() {
    history.push('/workflows/initiate/basic');
  }
};

export default WorkflowList;
