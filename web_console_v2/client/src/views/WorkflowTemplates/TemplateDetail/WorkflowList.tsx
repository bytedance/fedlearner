import React, { FC, useMemo } from 'react';
import styled from './WorkflowList.module.less';
import { Table, Message, Spin } from '@arco-design/web-react';
import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { fetchWorkflowListByRevisionId } from 'services/workflow';
import i18n from 'i18n';
import { formatTimestamp } from 'shared/date';
import { Workflow, WorkflowState, WorkflowStateFilterParam } from 'typings/workflow';
import WorkflowStage from './WorkflowStage';
import WhichProject from 'components/WhichProject';
import { useUrlState, useTablePaginationWithUrlState, useGetCurrentProjectId } from 'hooks';
import { TIME_INTERVAL } from 'shared/constants';

type TableColumnsOptions = {
  onSuccess?: Function;
  withoutActions?: boolean;
  defaultFavourFilteredValue?: string[];
  onForkableChange?: (record: Workflow, val: boolean) => void;
  onFavourSwitchChange?: (record: Workflow) => void;
};

export const getWorkflowTableColumns = (options: TableColumnsOptions = {}) => {
  const ret = [
    {
      title: i18n.t('workflow.name'),
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (name: string, record: Workflow) => {
        const { state } = record;
        const { INVALID } = WorkflowState;
        return (
          <>
            <Link
              className={styled.name_link}
              to={`/workflow-center/workflows/${record.id}`}
              rel="nopener"
              data-invalid={state === INVALID}
            >
              {name}
            </Link>
            <small className={styled.uuid_container}>uuid: {record.uuid}</small>
          </>
        );
      },
    },
    {
      title: i18n.t('workflow.col_status'),
      dataIndex: 'state',
      width: 120,
      render: (_: string, record: Workflow) => <WorkflowStage workflow={record} />,
    },
    {
      title: i18n.t('workflow.col_project'),
      dataIndex: 'project_id',
      width: 150,
      render: (project_id: number) => <WhichProject id={project_id} />,
    },
    {
      title: i18n.t('workflow.col_date'),
      dataIndex: 'created_at',
      width: 150,
      render: (date: number) => <div>{formatTimestamp(date)}</div>,
    },
  ];

  return ret;
};

type QueryParams = {
  project?: string;
  keyword?: string;
  uuid?: string;
  states?: WorkflowStateFilterParam[];
  page?: number;
};

export const WORKFLOW_LIST_QUERY_KEY = 'fetchWorkflowListByRevisionId';
interface Props {
  revisionId: number;
}

const WorkflowList: FC<Props> = (props) => {
  const [urlState, setUrlState] = useUrlState<QueryParams>({ keyword: '', uuid: '', states: [] });
  const projectId = useGetCurrentProjectId();
  const { revisionId } = props;

  const { urlState: pageInfoState, paginationProps } = useTablePaginationWithUrlState();
  const listQueryKey = [
    WORKFLOW_LIST_QUERY_KEY,
    urlState.keyword,
    urlState.uuid,
    urlState.states,
    projectId,
    pageInfoState.page,
    pageInfoState.pageSize,
    revisionId,
  ];
  const listQuery = useQuery(
    listQueryKey,
    () => {
      return fetchWorkflowListByRevisionId(projectId || 0, {
        // template_revision_id is available only Revision Item is clicked
        template_revision_id: revisionId,
      });
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST,
    },
  );
  const { isLoading, isError, data: res, error, refetch } = listQuery;

  if (isError && error) {
    Message.error((error as Error).message);
  }

  const workflowListShow = useMemo(() => {
    const workflowList = res?.data ?? [];
    return workflowList;
  }, [res]);

  return (
    <Spin loading={isLoading}>
      <div className={styled.list_container}>
        <Table
          className="custom-table custom-table-left-side-filter"
          data={workflowListShow}
          columns={getWorkflowTableColumns({
            onSuccess,
          })}
          onChange={(_, filter, sorter, extra) => {
            if (extra.action === 'filter') {
              setUrlState({
                page: 1,
              });
            }
          }}
          scroll={{ x: '100%' }}
          rowKey="name"
          pagination={{
            ...paginationProps,
            total: listQuery.data?.page_meta?.total_items ?? undefined,
          }}
        />
      </div>
    </Spin>
  );

  function onSuccess() {
    refetch();
  }
};

export default WorkflowList;
