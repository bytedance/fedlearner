import React, { FC, useEffect, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { useToggle } from 'react-use';
import { Button, Input, Table } from '@arco-design/web-react';
import { useUrlState } from 'hooks';
import { fetchCleanupList, postCleanupState } from 'services/cleanup';
import { Cleanup, CleanupState } from 'typings/cleanup';
import { FilterOp } from 'typings/filter';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import SharedPageLayout from 'components/SharedPageLayout';
import GridRow from 'components/_base/GridRow';
import { constructExpressionTree, expression2Filter } from 'shared/filter';
import { formatTimestamp } from 'shared/date';
import CONSTANTS from 'shared/constants';
import styled from './index.module.less';
import CleanupDetailDrawer from '../CleanupDetailDrawer';

export type QueryParams = {
  state?: CleanupState;
  resource_type?: string;
  resource_id?: string;
};

export const calcStateIndicatorProps = (
  state?: CleanupState,
): { type: StateTypes; text: string; tip?: string } => {
  let text = CONSTANTS.EMPTY_PLACEHOLDER;
  let type = 'default' as StateTypes;
  const tip = '';

  switch (state) {
    case CleanupState.WAITING:
      text = '等待中';
      type = 'gold';
      break;
    case CleanupState.CANCELED:
      text = '已撤销';
      type = 'default';
      break;
    case CleanupState.RUNNING:
      text = '运行中';
      type = 'processing';
      break;
    case CleanupState.FAILED:
      text = '失败';
      type = 'error';
      break;
    case CleanupState.SUCCEEDED:
      text = '成功';
      type = 'success';
      break;
  }

  return {
    text,
    type,
    tip,
  };
};

const CleanupList: FC = () => {
  const [isDrawerVisible, setIsDrawerVisible] = useToggle(false);
  const [selectedCleanup, setSelectedCleanup] = useState<Cleanup>();
  const [urlState, setUrlState] = useUrlState({
    page: 1,
    pageSize: 10,
    filter: '',
  });

  const initFilterParams = expression2Filter(urlState.filter);
  const [filterParams, setFilterParams] = useState<QueryParams>({
    state: initFilterParams.state,
    resource_type: initFilterParams.resource_type,
    resource_id: initFilterParams.resource_id,
  });

  const listQ = useQuery(
    ['CLEANUP_QUERY_KEY', urlState],
    () =>
      fetchCleanupList({
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

    return listQ.data.data || [];
  }, [listQ.data]);

  const columns = useMemo(
    () => [
      {
        title: 'ID',
        dataIndex: 'id',
        name: 'id',
        render: (_: any, record: Cleanup) => (
          <span
            className={styled.link_text}
            onClick={() => {
              setSelectedCleanup(record);
              setIsDrawerVisible(true);
            }}
          >
            {record.id}
          </span>
        ),
      },
      {
        title: '状态',
        dataIndex: 'state',
        name: 'state',
        filters: [
          {
            text: '等待中',
            value: CleanupState.WAITING,
          },
          {
            text: '运行中',
            value: CleanupState.RUNNING,
          },
          {
            text: '已撤销',
            value: CleanupState.CANCELED,
          },
          {
            text: '失败',
            value: CleanupState.FAILED,
          },
          {
            text: '成功',
            value: CleanupState.SUCCEEDED,
          },
        ],
        defaultFilters: filterParams.state ? [filterParams.state as string] : [],
        filterMultiple: false,
        render: (_: any, record: Cleanup) => {
          return <StateIndicator {...calcStateIndicatorProps(record.state)} />;
        },
      },
      {
        title: '目标开始时间',
        dataIndex: 'target_start_at',
        name: 'target_start_at',
        render: (_: any, record: Cleanup) => (
          <span>
            {record.target_start_at
              ? formatTimestamp(record.target_start_at)
              : CONSTANTS.EMPTY_PLACEHOLDER}
          </span>
        ),
      },
      {
        title: '完成时间',
        dataIndex: 'completed_at',
        name: 'completed_at',
        render: (_: any, record: Cleanup) => (
          <span>
            {record.completed_at
              ? formatTimestamp(record.completed_at)
              : CONSTANTS.EMPTY_PLACEHOLDER}
          </span>
        ),
      },
      {
        title: 'Resource ID',
        dataIndex: 'resource_id',
        name: 'resource_id',
        render: (_: any, record: Cleanup) => <span>{record.resource_id}</span>,
      },
      {
        title: '资源类型',
        dataIndex: 'resource_type',
        name: 'resource_type',
        render: (_: any, record: Cleanup) => <span>{record.resource_type}</span>,
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        name: 'created_at',
        render: (_: any, record: Cleanup) => (
          <span>
            {record.created_at ? formatTimestamp(record.created_at) : CONSTANTS.EMPTY_PLACEHOLDER}
          </span>
        ),
      },
      {
        title: '更新时间',
        dataIndex: 'updated_at',
        name: 'updated_at',
        render: (_: any, record: Cleanup) => (
          <span>
            {record.updated_at ? formatTimestamp(record.updated_at) : CONSTANTS.EMPTY_PLACEHOLDER}
          </span>
        ),
      },
      {
        title: '操作',
        dataIndex: 'operation',
        name: 'operation',
        width: 200,
        render: (_: any, record: Cleanup) => {
          return (
            <Button
              disabled={record.state !== CleanupState.WAITING}
              onClick={() => {
                postCleanupState(record.id).then(() => {
                  listQ.refetch();
                });
              }}
            >
              取消
            </Button>
          );
        },
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
    <SharedPageLayout title="Cleanup">
      <GridRow justify="end" align="center">
        <Input.Search
          style={{ paddingRight: 20 }}
          allowClear
          defaultValue={filterParams.resource_type}
          placeholder={'请输入资源类型'}
          onSearch={onResourceTypeSearch}
          onClear={() => onResourceTypeSearch('')}
        />
        <Input.Search
          allowClear
          defaultValue={filterParams.resource_id}
          placeholder={'请输入resource id'}
          onSearch={onResourceIdSearch}
          onClear={() => onResourceIdSearch('')}
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
              state: (filters.state?.[0] as CleanupState) ?? undefined,
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
      <CleanupDetailDrawer
        visible={isDrawerVisible}
        data={selectedCleanup}
        onCancel={onCleanupDetailDrawerClose}
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

  function onResourceTypeSearch(value: any) {
    setFilterParams({
      ...filterParams,
      resource_type: value,
    });
  }

  function onResourceIdSearch(value: any) {
    setFilterParams({
      ...filterParams,
      resource_id: value,
    });
  }

  function constructFilterArray(value: QueryParams) {
    const expressionNodes = [];

    if (value.state) {
      expressionNodes.push({
        field: 'state',
        op: FilterOp.EQUAL,
        string_value: value.state,
      });
    }
    if (value.resource_type) {
      expressionNodes.push({
        field: 'resource_type',
        op: FilterOp.EQUAL,
        string_value: value.resource_type,
      });
    }
    if (value.resource_id) {
      expressionNodes.push({
        field: 'resource_id',
        op: FilterOp.EQUAL,
        string_value: value.resource_id,
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

  function onCleanupDetailDrawerClose() {
    setSelectedCleanup(undefined);
    setIsDrawerVisible(false);
  }
};

export default CleanupList;
