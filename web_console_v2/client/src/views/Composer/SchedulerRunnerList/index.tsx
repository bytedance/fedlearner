import React, { FC, useEffect, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import SharedPageLayout from 'components/SharedPageLayout';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import { Table } from '@arco-design/web-react';
import { useUrlState } from 'hooks';
import { RunnerStatus, SchedulerRunner } from 'typings/composer';
import { FilterOp } from 'typings/filter';
import { fetchSchedulerRunnerList } from 'services/composer';
import { constructExpressionTree, expression2Filter } from 'shared/filter';
import { formatTimestamp } from 'shared/date';
import { Link } from 'react-router-dom';
import { filterExpressionGenerator } from 'views/Datasets/shared';
import { TABLE_COL_WIDTH } from 'shared/constants';
import SchedulerRunnerActions from './SchedulerRunnerActions';
import { ColumnProps } from '@arco-design/web-react/es/Table';
import CONSTANTS from 'shared/constants';

export type QueryParams = {
  status?: RunnerStatus;
};

const calcStateIndicatorProps = (
  state: RunnerStatus,
): { type: StateTypes; text: string; tip?: string } => {
  let text = CONSTANTS.EMPTY_PLACEHOLDER;
  let type = 'default' as StateTypes;
  const tip = '';

  switch (state) {
    case RunnerStatus.INIT:
      text = '初始化';
      type = 'gold';
      break;
    case RunnerStatus.RUNNING:
      text = '运行中';
      type = 'processing';
      break;
    case RunnerStatus.FAILED:
      text = '运行失败';
      type = 'error';
      break;
    case RunnerStatus.DONE:
      text = '已结束';
      type = 'success';
      break;
    default:
      break;
  }

  return {
    text,
    type,
    tip,
  };
};

const SchedulerRunnerList: FC = () => {
  const [urlState, setUrlState] = useUrlState({
    page: 1,
    pageSize: 10,
    filter: '',
  });

  const initFilterParams = expression2Filter(urlState.filter);
  const [filterParams, setFilterParams] = useState<QueryParams>({
    status: initFilterParams.status,
  });

  const listQ = useQuery(
    ['SCHEDULE_RUNNER_QUERY_KEY', urlState],
    () =>
      fetchSchedulerRunnerList({
        page: urlState.page,
        pageSize: urlState.pageSize,
        filter: urlState.filter === '' ? undefined : urlState.filter,
      }),
    {
      refetchOnWindowFocus: false,
      keepPreviousData: true,
    },
  );

  // Filter the display list by the search string
  const runnerListShow = useMemo(() => {
    if (!listQ.data?.data) {
      return [];
    }
    const templateList = listQ.data.data || [];
    return templateList;
  }, [listQ.data]);

  const columns: ColumnProps[] = useMemo(
    () => [
      {
        title: '调度项ID',
        dataIndex: 'item_id',
        name: 'item_id',
        width: TABLE_COL_WIDTH.NAME,
        render: (_: any, record: SchedulerRunner) => {
          const filter = filterExpressionGenerator(
            {
              id: record.item_id,
            },
            {
              id: FilterOp.EQUAL,
            },
          );
          return (
            <Link
              to={(location) => ({
                ...location,
                pathname: `/composer/scheduler-item/list`,
                search: location.search
                  ? `${location.search}&filter=${filter}`
                  : `?filter=${filter}`,
              })}
            >
              {record.item_id}
            </Link>
          );
        },
      },
      {
        title: '状态',
        dataIndex: 'status',
        name: 'status',
        width: TABLE_COL_WIDTH.NORMAL,
        filters: [
          {
            text: '初始化',
            value: RunnerStatus.INIT,
          },
          {
            text: '运行中',
            value: RunnerStatus.RUNNING,
          },
          {
            text: '已结束',
            value: RunnerStatus.DONE,
          },
          {
            text: '运行失败',
            value: RunnerStatus.FAILED,
          },
        ],
        defaultFilters: filterParams.status ? [filterParams.status as string] : [],
        filterMultiple: false,
        render: (_: any, record: SchedulerRunner) => {
          return <StateIndicator {...calcStateIndicatorProps(record.status)} />;
        },
      },
      {
        title: '开始时间',
        dataIndex: 'start_at',
        name: 'start_at',
        width: TABLE_COL_WIDTH.NORMAL,
        render: (_: any, record: SchedulerRunner) => (
          <span>{formatTimestamp(record.start_at)}</span>
        ),
      },
      {
        title: '结束时间',
        dataIndex: 'end_at',
        name: 'end_at',
        width: TABLE_COL_WIDTH.NORMAL,
        render: (_: any, record: SchedulerRunner) => (
          <span>
            {record.end_at ? formatTimestamp(record.end_at) : CONSTANTS.EMPTY_PLACEHOLDER}
          </span>
        ),
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        name: 'created_at',
        width: TABLE_COL_WIDTH.NORMAL,
        render: (_: any, record: SchedulerRunner) => (
          <span>{formatTimestamp(record.created_at)}</span>
        ),
      },
      {
        title: '更新时间',
        dataIndex: 'updated_at',
        name: 'updated_at',
        width: TABLE_COL_WIDTH.NORMAL,
        render: (_: any, record: SchedulerRunner) => (
          <span>{formatTimestamp(record.updated_at)}</span>
        ),
      },
      {
        title: '删除时间',
        dataIndex: 'deleted_at',
        name: 'deleted_at',
        width: TABLE_COL_WIDTH.NORMAL,
        render: (_: any, record: SchedulerRunner) => (
          <span>
            {record.deleted_at ? formatTimestamp(record.deleted_at!) : CONSTANTS.EMPTY_PLACEHOLDER}
          </span>
        ),
      },
      {
        title: '操作',
        dataIndex: 'operation',
        name: 'operation',
        fixed: 'right',
        width: TABLE_COL_WIDTH.NORMAL,
        render: (_: number, record: SchedulerRunner) => (
          <SchedulerRunnerActions scheduler={record} />
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [listQ],
  );

  useEffect(() => {
    constructFilterArray(filterParams);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterParams]);

  return (
    <SharedPageLayout title="调度程序运行器">
      <Table
        loading={listQ.isFetching}
        data={runnerListShow}
        columns={columns}
        scroll={{ x: '100%' }}
        rowKey="id"
        onChange={(_, sorter, filters, extra) => {
          if (extra.action === 'filter') {
            setFilterParams({
              status: (filters.status?.[0] as RunnerStatus) ?? undefined,
            });
          }
        }}
        pagination={{
          total: listQ.data?.page_meta?.total_items ?? undefined,
          current: Number(urlState.page),
          pageSize: Number(urlState.pageSize),
          onChange: onPageChange,
          showTotal: (total: number) => `共 ${total} 条记录`,
        }}
      />
    </SharedPageLayout>
  );

  function onPageChange(page: number, pageSize: number | undefined) {
    setUrlState((prevState) => ({
      ...prevState,
      page,
      pageSize,
    }));
  }

  function constructFilterArray(value: QueryParams) {
    const expressionNodes = [];

    if (value.status) {
      expressionNodes.push({
        field: 'status',
        op: FilterOp.EQUAL,
        string_value: value.status,
      });
    }

    const serialization = constructExpressionTree(expressionNodes);
    if ((serialization || urlState.filter) && serialization !== urlState.filter) {
      setUrlState((prevState) => ({
        ...prevState,
        filter: serialization,
        page: 1,
      }));
    }
  }
};

export default SchedulerRunnerList;
