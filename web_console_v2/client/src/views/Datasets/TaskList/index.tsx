import React, { FC, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import {
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantId,
  useGetCurrentProjectParticipantList,
  useTablePaginationWithUrlState,
  useUrlState,
} from 'hooks';
import { fetchDatasetJobList } from 'services/dataset';
import { TABLE_COL_WIDTH, TIME_INTERVAL } from 'shared/constants';
import { formatTimestamp } from 'shared/date';
import { getDatasetJobState } from 'shared/dataset';
import {
  datasetJobStateFilters,
  datasetJobTypeFilters,
  FILTER_DATA_JOB_OPERATOR_MAPPER,
  filterExpressionGenerator,
  getJobKindByFilter,
  getJobStateByFilter,
  getSortOrder,
} from '../shared';

import { Button, Input, Message, Table, TableColumnProps } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import SharedPageLayout from 'components/SharedPageLayout';
import StateIndicator from 'components/StateIndicator';
import DatasetJobsType from 'components/DatasetJobsType';
import WhichParticipant from 'components/WhichParticipant';
import { Link } from 'react-router-dom';

import { ColumnProps } from '@arco-design/web-react/es/Table';
import { DataJobBackEndType, DatasetJobListItem, DatasetJobState } from 'typings/dataset';
import TaskActions from './TaskActions';
import { expression2Filter } from 'shared/filter';
import { useToggle } from 'react-use';
import './index.less';

type TProps = {};
type TableFilterConfig = Pick<TableColumnProps, 'filters' | 'onFilter'>;
const { Search } = Input;

const List: FC<TProps> = function (props: TProps) {
  const { paginationProps } = useTablePaginationWithUrlState();
  const projectId = useGetCurrentProjectId();
  const participantId = useGetCurrentProjectParticipantId();
  const participantList = useGetCurrentProjectParticipantList();
  const [total, setTotal] = useState(0);
  const [isViewRunning, setIsViewRunning] = useToggle(false);
  const [pageTotal, setPageTotal] = useState(0);

  // Temporarily get the number of running tasks by calling the list-api again;
  const runningCountQuery = useQuery(
    ['fetchRunningCount', projectId],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return;
      }
      return fetchDatasetJobList(projectId!, {
        page: 1,
        page_size: 1,
        filter: filterExpressionGenerator(
          {
            state: [DatasetJobState.RUNNING, DatasetJobState.PENDING],
          },
          FILTER_DATA_JOB_OPERATOR_MAPPER,
        ),
      });
    },
    {
      refetchInterval: TIME_INTERVAL.LIST,
    },
  );

  // get participantFilter from participantList
  const datasetJobCoordinatorFilters: TableFilterConfig = useMemo(() => {
    let filters: { text: string; value: any }[] = [];
    if (Array.isArray(participantList) && participantList.length) {
      filters = participantList.map((item) => ({
        text: item.name,
        value: item.id,
      }));
      filters.push({
        text: '本方',
        value: 0,
      });
    }
    return {
      filters,
      onFilter: (value: number, record: DatasetJobListItem) => {
        return value === record.coordinator_id;
      },
    };
  }, [participantList]);

  // store filter status into urlState
  const [urlState, setUrlState] = useUrlState({
    filter: '',
    order_by: '',
    page: 1,
    pageSize: 10,
  });

  // generator listQuery
  const listQuery = useQuery(
    ['fetchDatasetJobList', projectId, urlState],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return;
      }
      const filter = expression2Filter(urlState.filter);
      filter.state = getJobStateByFilter(filter.state);
      filter.kind = getJobKindByFilter(filter.kind);
      return fetchDatasetJobList(projectId!, {
        page: urlState.page,
        page_size: urlState.pageSize,
        filter: filterExpressionGenerator(filter, FILTER_DATA_JOB_OPERATOR_MAPPER),
        order_by: urlState.order_by || 'created_at desc',
      });
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST,
      refetchOnWindowFocus: false,
      onSuccess: (res) => {
        const { page_meta } = res || {};
        setTotal((pre) => page_meta?.total_items || pre);
        setPageTotal(page_meta?.total_pages ?? 0);
      },
    },
  );

  // generator listData from listQuery and watch listQuery
  const list = useMemo(() => {
    return listQuery.data?.data || [];
  }, [listQuery.data]);

  const runningCount = useMemo(() => {
    if (!runningCountQuery.data) {
      return 0;
    } else {
      return runningCountQuery.data?.page_meta?.total_items || 0;
    }
  }, [runningCountQuery.data]);

  const columns = useMemo<ColumnProps<DatasetJobListItem>[]>(() => {
    return [
      {
        title: '任务名称',
        dataIndex: 'name',
        key: 'name',
        width: TABLE_COL_WIDTH.NAME,
        ellipsis: true,
        render: (name: string, record) => {
          if (record.has_stages) {
            // 新数据跳转新任务详情
            return (
              <Link to={`/datasets/${record.result_dataset_id}/new/job_detail/${record.id}`}>
                {name}
              </Link>
            );
          }
          return <Link to={`/datasets/job_detail/${record.id}`}>{name}</Link>;
        },
      },
      {
        title: '任务类型',
        dataIndex: 'kind',
        key: 'kind',
        width: TABLE_COL_WIDTH.NORMAL,
        ...datasetJobTypeFilters,
        filteredValue: expression2Filter(urlState.filter).kind,
        render: (type) => {
          return <DatasetJobsType type={type as DataJobBackEndType} />;
        },
      },
      {
        title: '任务状态',
        dataIndex: 'state',
        key: 'state',
        width: TABLE_COL_WIDTH.NORMAL,
        ...datasetJobStateFilters,
        filteredValue: expression2Filter(urlState.filter).state,
        render: (_: any, record: DatasetJobListItem) => {
          return (
            <div className="indicator-with-tip">
              <StateIndicator {...getDatasetJobState(record)} />
            </div>
          );
        },
      },
      {
        title: '任务发起方',
        dataIndex: 'coordinator_id',
        key: 'coordinator_id',
        width: TABLE_COL_WIDTH.COORDINATOR,
        ...datasetJobCoordinatorFilters,
        filteredValue: expression2Filter(urlState.filter).coordinator_id,
        render: (value: any) => {
          return value === 0 ? '本方' : <WhichParticipant id={value} />;
        },
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        key: 'created_at',
        width: TABLE_COL_WIDTH.TIME,
        sorter(a: DatasetJobListItem, b: DatasetJobListItem) {
          return a.created_at - b.created_at;
        },
        defaultSortOrder: getSortOrder(urlState, 'created_at'),
        render: (date: number) => <div>{formatTimestamp(date)}</div>,
      },
      {
        title: '操作',
        dataIndex: 'state',
        key: 'operation',
        fixed: 'right',
        width: TABLE_COL_WIDTH.NORMAL,
        render: (state: DatasetJobState, record) => (
          <TaskActions
            buttonProps={{
              type: 'text',
              className: 'custom-text-button',
            }}
            data={record}
            onDelete={listQuery.refetch}
            onStop={handleRefetch}
          />
        ),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlState, projectId, participantId]);

  // filter running jobs
  const handleOnClick = () => {
    const filter = expression2Filter(urlState.filter);
    filter.state = isViewRunning ? undefined : [DatasetJobState.RUNNING];
    setUrlState((prevState) => ({
      ...prevState,
      page: 1,
      filter: filterExpressionGenerator(filter, FILTER_DATA_JOB_OPERATOR_MAPPER),
    }));
    setIsViewRunning((pre: boolean) => !pre);
  };

  // search by keyword
  const onSearch = (value: string) => {
    const filter = expression2Filter(urlState.filter);
    filter.name = value;
    setUrlState((prevState) => ({
      ...prevState,
      page: 1,
      filter: filterExpressionGenerator(filter, FILTER_DATA_JOB_OPERATOR_MAPPER),
    }));
  };

  const pagination = useMemo(() => {
    return pageTotal <= 1
      ? false
      : {
          ...paginationProps,
          total,
        };
  }, [paginationProps, pageTotal, total]);

  return (
    <SharedPageLayout title="任务管理">
      <GridRow justify="space-between" align="center">
        <Button className={'custom-operation-button'} onClick={handleOnClick}>
          查看运行中任务
          <span className="task-running-count-wrapper">{runningCount}</span>
        </Button>
        <Search
          className={'custom-input'}
          allowClear
          placeholder="输入任务名称"
          defaultValue={expression2Filter(urlState.filter).name}
          onSearch={onSearch}
          onClear={() => onSearch('')}
        />
      </GridRow>
      <Table
        className={'custom-table custom-table-left-side-filter'}
        rowKey="id"
        loading={listQuery.isFetching}
        data={list}
        scroll={{ x: '100%' }}
        columns={columns}
        pagination={pagination}
        onChange={(
          pagination,
          sorter,
          filters: Partial<Record<keyof DatasetJobListItem, any[]>>,
          extra,
        ) => {
          switch (extra.action) {
            case 'sort':
              let orderValue = '';
              if (sorter.direction) {
                orderValue = sorter.direction === 'ascend' ? 'asc' : 'desc';
              }
              setUrlState((prevState) => ({
                ...prevState,
                order_by: orderValue ? `${sorter.field} ${orderValue}` : '',
              }));
              break;
            case 'filter':
              const filterCopy = {
                ...filters,
                name: expression2Filter(urlState.filter).name,
              };
              setUrlState((prevState) => ({
                ...prevState,
                filter: filterExpressionGenerator(filterCopy, FILTER_DATA_JOB_OPERATOR_MAPPER),
                page: 1,
              }));
              break;
            default:
          }
        }}
      />
    </SharedPageLayout>
  );
  function handleRefetch() {
    listQuery.refetch();
    runningCountQuery.refetch();
  }
};

export default List;
