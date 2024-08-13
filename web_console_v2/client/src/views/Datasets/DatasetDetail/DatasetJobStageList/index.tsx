import React, { FC, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { useTablePaginationWithUrlState, useUrlState, useGetCurrentProjectId } from 'hooks';
import { fetchDatasetJobStageList } from 'services/dataset';
import { TABLE_COL_WIDTH, TIME_INTERVAL } from 'shared/constants';
import { formatTimestamp } from 'shared/date';
import {
  datasetJobStateFilters,
  FILTER_DATA_BATCH_OPERATOR_MAPPER,
  filterExpressionGenerator,
  getSortOrder,
  getJobKindByFilter,
  getJobStateByFilter,
} from '../../shared';
import { Table, Message } from '@arco-design/web-react';
import StateIndicator from 'components/StateIndicator';
import DatasetJobsType from 'components/DatasetJobsType';
import { Link } from 'react-router-dom';
import { getDatasetJobState } from 'shared/dataset';
import { ColumnProps } from '@arco-design/web-react/es/Table';
import { DatasetJobStage, DataJobBackEndType } from 'typings/dataset';
import { expression2Filter } from 'shared/filter';
import { LabelStrong } from 'styles/elements';
import { JobDetailSubTabs } from 'views/Datasets/NewDatasetJobDetail';
import styled from './index.module.less';

type TProps = {
  datasetId: ID;
  datasetJobId: ID;
};
const DataBatchTable: FC<TProps> = function (props: TProps) {
  const { datasetJobId, datasetId } = props;
  const projectId = useGetCurrentProjectId();
  const { paginationProps } = useTablePaginationWithUrlState();
  const [total, setTotal] = useState(0);
  const [pageTotal, setPageTotal] = useState(0);

  // store filter status into urlState
  const [urlState, setUrlState] = useUrlState({
    filter: '',
    order_by: '',
    page: 1,
    pageSize: 10,
  });

  // generator listQuery
  const listQuery = useQuery(
    ['fetchDatasetJobStageList', projectId, datasetJobId, urlState],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return;
      }
      const filter = expression2Filter(urlState.filter);
      filter.state = getJobStateByFilter(filter.state);
      filter.kind = getJobKindByFilter(filter.kind);
      return fetchDatasetJobStageList(projectId!, datasetJobId, {
        page: urlState.page,
        page_size: urlState.pageSize,
        order_by: urlState.order_by,
        filter: filterExpressionGenerator(filter, FILTER_DATA_BATCH_OPERATOR_MAPPER),
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

  const columns = useMemo<ColumnProps<DatasetJobStage>[]>(() => {
    return [
      {
        title: '任务名称',
        dataIndex: 'name',
        key: 'name',
        width: TABLE_COL_WIDTH.NAME,
        ellipsis: true,
        render: (name: string, record) => {
          return (
            <Link
              to={(location) => ({
                ...location,
                pathname: `/datasets/${datasetId}/new/job_detail/${record.dataset_job_id}/${JobDetailSubTabs.TaskList}`,
                search: location.search
                  ? `${location.search}&stageId=${record.id}`
                  : `?stageId=${record.id}`,
              })}
            >
              {name}
            </Link>
          );
        },
      },
      {
        title: '任务类型',
        dataIndex: 'kind',
        key: 'kind',
        width: TABLE_COL_WIDTH.NORMAL,
        // ...datasetJobTypeFilters,
        // filteredValue: expression2Filter(urlState.filter).kind,
        render: (type) => {
          return <DatasetJobsType type={type as DataJobBackEndType} />;
        },
      },
      {
        title: '状态',
        dataIndex: 'state',
        key: 'state',
        width: TABLE_COL_WIDTH.NORMAL,
        ...datasetJobStateFilters,
        filteredValue: expression2Filter(urlState.filter).state,
        render: (_: any, record: DatasetJobStage) => {
          return (
            <div className="indicator-with-tip">
              <StateIndicator {...getDatasetJobState(record)} />
            </div>
          );
        },
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        key: 'created_at',
        width: TABLE_COL_WIDTH.TIME,
        sorter(a: DatasetJobStage, b: DatasetJobStage) {
          return a.created_at - b.created_at;
        },
        defaultSortOrder: getSortOrder(urlState, 'created_at'),
        render: (date: number) => <div>{formatTimestamp(date)}</div>,
      },
    ];
  }, [urlState, datasetId]);

  const pagination = useMemo(() => {
    return pageTotal <= 1
      ? false
      : {
          ...paginationProps,
          total,
        };
  }, [paginationProps, pageTotal, total]);

  return (
    <>
      <LabelStrong fontSize={14} isBlock={true}>
        任务列表
      </LabelStrong>
      <Table
        className={`custom-table custom-table-left-side-filter ${styled.table}`}
        rowKey="id"
        loading={listQuery.isFetching}
        data={list}
        scroll={{ x: '100%' }}
        columns={columns}
        pagination={pagination}
        onChange={(
          pagination,
          sorter,
          filters: Partial<Record<keyof DatasetJobStage, any[]>>,
          extra,
        ) => {
          switch (extra.action) {
            case 'sort': {
              let orderValue: string;
              if (sorter.direction) {
                orderValue = sorter.direction === 'ascend' ? 'asc' : 'desc';
              }
              setUrlState((prevState) => ({
                ...prevState,
                order_by: orderValue ? `${sorter.field} ${orderValue}` : '',
              }));
              break;
            }
            case 'filter':
              setUrlState((prevState) => ({
                ...prevState,
                filter: filterExpressionGenerator(
                  {
                    ...filters,
                  },
                  FILTER_DATA_BATCH_OPERATOR_MAPPER,
                ),
                page: 1,
              }));
              break;
            default:
          }
        }}
      />
    </>
  );
};

export default DataBatchTable;
