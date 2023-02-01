import React, { FC, useEffect, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import { Input, Switch, Table } from '@arco-design/web-react';
import SharedPageLayout from 'components/SharedPageLayout';
import GridRow from 'components/_base/GridRow';
import { useUrlState } from 'hooks';
import { FilterOp } from 'typings/filter';
import { ItemStatus, SchedulerItem } from 'typings/composer';
import { fetchSchedulerItemList, patchEditItemState } from 'services/composer';
import { constructExpressionTree, expression2Filter } from 'shared/filter';
import { formatTimestamp } from 'shared/date';
import SchedulerItemActions from './SchedulerItemActions';
import { ColumnProps } from '@arco-design/web-react/es/Table';
import { TABLE_COL_WIDTH } from 'shared/constants';
import CONSTANTS from 'shared/constants';

export type QueryParams = {
  is_cron?: boolean;
  status?: ItemStatus;
  name?: string;
  id?: string;
};

const SchedulerItemList: FC = () => {
  const [urlState, setUrlState] = useUrlState({
    page: 1,
    pageSize: 10,
    filter: '',
  });
  const initFilterParams = expression2Filter(urlState.filter);
  const [filterParams, setFilterParams] = useState<QueryParams>({
    is_cron: initFilterParams.is_cron || false,
    status: initFilterParams.status,
    name: initFilterParams.name || '',
    id: initFilterParams.id,
  });

  const listQ = useQuery(
    ['SCHEDULE_ITEM_QUERY_KEY', urlState],
    () =>
      fetchSchedulerItemList({
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
  const itemListShow = useMemo(() => {
    if (!listQ.data?.data) {
      return [];
    }
    const templateList = listQ.data.data || [];
    return templateList;
  }, [listQ.data]);

  const columns: ColumnProps[] = useMemo(
    () => [
      {
        title: '名称',
        dataIndex: 'name',
        name: 'name',
        width: TABLE_COL_WIDTH.NAME,
        render: (name: string, record: SchedulerItem) => (
          <Link
            to={`/composer/scheduler-item/detail/${record.id}`}
            rel="nopener"
            className="col-name-link"
          >
            {name}
          </Link>
        ),
      },
      {
        title: '状态',
        dataIndex: 'status',
        name: 'status',
        width: TABLE_COL_WIDTH.NORMAL,
        filters: [
          {
            text: '开启',
            value: ItemStatus.ON,
          },
          {
            text: '关闭',
            value: ItemStatus.OFF,
          },
        ],
        defaultFilters: filterParams.status ? [filterParams.status as string] : [],
        filterMultiple: false,
        render: (_: any, record: SchedulerItem) => {
          <span>{record.status}</span>;
          return (
            <Switch
              size="small"
              onChange={(value: boolean) => {
                patchEditItemState(record.id, value ? ItemStatus.ON : ItemStatus.OFF).then(() => {
                  listQ.refetch();
                });
              }}
              checked={record.status === ItemStatus.ON}
            />
          );
        },
      },
      {
        title: 'cron_config',
        dataIndex: 'cron_config',
        name: 'cron_config',
        width: TABLE_COL_WIDTH.NORMAL,
        filters: [
          {
            text: '展示cron_job_items',
            value: true,
          },
          {
            text: '展示all items',
            value: false,
          },
        ],
        filterMultiple: false,
        render: (_: any, record: SchedulerItem) => <span>{record.cron_config}</span>,
      },
      {
        title: '最近运行时间',
        dataIndex: 'last_run_at',
        name: 'last_run_at',
        width: TABLE_COL_WIDTH.TIME,
        render: (_: any, record: SchedulerItem) => (
          <span>{formatTimestamp(record.last_run_at)}</span>
        ),
      },
      {
        title: 'retry_cnt',
        dataIndex: 'retry_cnt',
        name: 'retry_cnt',
        width: TABLE_COL_WIDTH.THIN,
        render: (_: any, record: SchedulerItem) => <span>{record.retry_cnt}</span>,
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        name: 'created_at',
        width: TABLE_COL_WIDTH.TIME,
        render: (_: any, record: SchedulerItem) => (
          <span>{formatTimestamp(record.created_at)}</span>
        ),
      },
      {
        title: '更新时间',
        dataIndex: 'updated_at',
        name: 'updated_at',
        width: TABLE_COL_WIDTH.NAME,
        render: (_: any, record: SchedulerItem) => (
          <span>{formatTimestamp(record.updated_at)}</span>
        ),
      },
      {
        title: '删除时间',
        dataIndex: 'deleted_at',
        name: 'deleted_at',
        width: TABLE_COL_WIDTH.TIME,
        render: (_: any, record: SchedulerItem) => (
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
        render: (_: number, record: SchedulerItem) => <SchedulerItemActions scheduler={record} />,
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
    <SharedPageLayout title="调度程序项">
      <GridRow justify="end" align="center">
        <Input.Search
          allowClear
          defaultValue={filterParams.name}
          onSearch={onSearch}
          onClear={() => onSearch('')}
          placeholder={'请输入名称'}
        />
      </GridRow>
      <Table
        loading={listQ.isFetching}
        data={itemListShow}
        columns={columns}
        scroll={{ x: '100%' }}
        rowKey="id"
        onChange={(_, sorter, filters, extra) => {
          if (extra.action === 'filter') {
            setFilterParams({
              ...filterParams,
              is_cron: Boolean(filters.cron_config?.[0]),
              status: (filters.status?.[0] as ItemStatus) ?? undefined,
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

  function onSearch(value: any) {
    setFilterParams({
      ...filterParams,
      name: value,
    });
  }

  function constructFilterArray(value: QueryParams) {
    const expressionNodes = [];
    if (value.is_cron) {
      expressionNodes.push({
        field: 'is_cron',
        op: FilterOp.EQUAL,
        bool_value: value.is_cron,
      });
    }
    if (value.name) {
      expressionNodes.push({
        field: 'name',
        op: FilterOp.CONTAIN,
        string_value: value.name,
      });
    }

    if (value.status) {
      expressionNodes.push({
        field: 'status',
        op: FilterOp.EQUAL,
        string_value: value.status,
      });
    }

    if (value.id) {
      expressionNodes.push({
        field: 'id',
        op: FilterOp.EQUAL,
        number_value: Number(value.id),
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

export default SchedulerItemList;
