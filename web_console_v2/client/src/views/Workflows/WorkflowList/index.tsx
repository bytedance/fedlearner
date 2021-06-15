import React, { FC, useEffect, useState } from 'react';
import styled from 'styled-components';
import { Row, Col, Button, Form, Input, Table, message, Spin } from 'antd';
import { Link, useHistory } from 'react-router-dom';
import { useQuery } from 'react-query';
import { fetchWorkflowList } from 'services/workflow';
import i18n from 'i18n';
import { formatTimestamp } from 'shared/date';
import { useTranslation } from 'react-i18next';
import SharedPageLayout from 'components/SharedPageLayout';
import { Workflow } from 'typings/workflow';
import WorkflowStage from './WorkflowStage';
import WorkflowActions from '../WorkflowActions';
import WhichProject from 'components/WhichProject';
import NoResult from 'components/NoResult';
import { projectState } from 'stores/project';
import { isInvalid } from 'shared/workflow';
import { useRecoilValue } from 'recoil';

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
const NameLink = styled(Link)`
  display: block;
  margin-bottom: 3px;
  font-size: 16px;

  &[data-invalid='true'] {
    color: var(--textColorDisabled);

    &:hover {
      color: var(--primaryColor);
    }
  }
`;
const UUID = styled.small`
  display: block;
  color: var(--textColorSecondary);
`;

export const getWorkflowTableColumns = (
  options: {
    onSuccess?: Function;
    withoutActions?: boolean;
    onForkableChange?: (record: Workflow, val: boolean) => void;
  } = {},
) => {
  const ret = [
    {
      title: i18n.t('workflow.name'),
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Workflow) => {
        return (
          <>
            <NameLink to={`/workflows/${record.id}`} rel="nopener" data-invalid={isInvalid(record)}>
              {name}
            </NameLink>
            <UUID>UUID: {record.uuid}</UUID>
          </>
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
      dataIndex: 'operation',
      name: 'operation',
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
  uuid?: string;
};

const WorkflowList: FC = () => {
  const { t } = useTranslation();
  const [form] = Form.useForm<QueryParams>();
  const history = useHistory();

  const [listData, setList] = useState<Workflow[]>([]);
  const [params, setParams] = useState<QueryParams>({ keyword: '', uuid: '' });

  const project = useRecoilValue(projectState);

  const { isLoading, isError, data: res, error, refetch } = useQuery(
    ['fetchWorkflowList', params.keyword, params.uuid, project.current?.id],
    () => fetchWorkflowList({ ...params, project: project.current?.id }),
  );

  if (isError && error) {
    message.error((error as Error).message);
  }

  useEffect(() => {
    setList(res?.data || []);
  }, [res?.data]);

  const isEmpty = listData.length === 0;

  return (
    <Spin spinning={isLoading}>
      <SharedPageLayout title={t('menu.label_workflow')}>
        <Row gutter={16} justify="space-between" align="middle">
          <Col>
            <Button size="large" type="primary" onClick={goCreate}>
              {t('workflow.create_workflow')}
            </Button>
          </Col>
          <Col>
            <Form
              initialValues={{ ...params }}
              layout="inline"
              form={form}
              onFinish={onParamsChange}
            >
              <FilterItem name="uuid">
                <Input.Search
                  placeholder={t('workflow.placeholder_uuid_searchbox')}
                  onPressEnter={form.submit}
                />
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
            <Table
              dataSource={listData}
              columns={getWorkflowTableColumns({ onSuccess })}
              scroll={{ x: '100%' }}
              rowKey="name"
            />
          )}
        </ListContainer>
      </SharedPageLayout>
    </Spin>
  );

  function onParamsChange(values: QueryParams) {
    // Set params will auto-trigger list query
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
