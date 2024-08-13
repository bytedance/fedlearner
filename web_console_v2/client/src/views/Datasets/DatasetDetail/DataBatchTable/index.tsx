import React, { FC, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { useTablePaginationWithUrlState, useUrlState } from 'hooks';
import { fetchDataBatchs } from 'services/dataset';
import { TABLE_COL_WIDTH, TIME_INTERVAL } from 'shared/constants';
import { formatTimestamp } from 'shared/date';
import { useParams, useHistory } from 'react-router';
import {
  dataBatchStateFilters,
  FILTER_DATA_BATCH_OPERATOR_MAPPER,
  filterExpressionGenerator,
  getSortOrder,
} from '../../shared';
import { Table, Tooltip, Typography, Message, Tag } from '@arco-design/web-react';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import ExportModal from 'components/DatasetExportModal';
import DatasetBatchRerunModal from './DatasetBatchRerunModal';
import { Link } from 'react-router-dom';
import { JobDetailSubTabs } from 'views/Datasets/NewDatasetJobDetail';
import { ColumnProps } from '@arco-design/web-react/es/Table';
import {
  DataBatchV2,
  DatasetStateFront,
  DatasetKindLabel,
  GlobalConfigs,
  DataJobBackEndType,
} from 'typings/dataset';
import { expression2Filter } from 'shared/filter';
import DataBatchActions from './DataBatchActions';
import DataBatchRate from './DataBatchRate';
import { humanFileSize } from 'shared/file';
import styled from './index.module.less';

const { Text } = Typography;

type Props = {
  datasetJobId: ID;
  isOldData: boolean;
  isDataJoin: boolean;
  isCopy: boolean;
  isInternalProcessed: boolean;
  kind: DataJobBackEndType;
  datasetRate: string;
  globalConfigs: GlobalConfigs;
};
const DataBatchTable: FC<Props> = function ({
  isOldData,
  isDataJoin,
  isCopy,
  isInternalProcessed,
  kind,
  datasetRate,
  datasetJobId,
  globalConfigs,
}: Props) {
  const { id, kind_label } = useParams<{
    id: string;
    kind_label: DatasetKindLabel;
  }>();
  const { paginationProps } = useTablePaginationWithUrlState();
  const [total, setTotal] = useState(0);
  const [pageTotal, setPageTotal] = useState(0);
  const [currentExportBatchId, setCurrentExportBatchId] = useState<ID>();
  const [isShowExportModal, setIsShowExportModal] = useState(false);
  const [currentRerunBatchId, setCurrentRerunBatchId] = useState<ID>();
  const [currentRerunBatchName, setCurrentRerunBatchName] = useState<string>('');
  const [isShowRerunModal, setIsShowRerunModal] = useState(false);
  const history = useHistory();

  // store filter status into urlState
  const [urlState, setUrlState] = useUrlState({
    filter: '',
    order_by: '',
    page: 1,
    pageSize: 10,
  });

  // generator listQuery
  const listQuery = useQuery(
    ['fetchDataBatchs', id, urlState],
    () => {
      return fetchDataBatchs(id!, {
        page: urlState.page,
        page_size: urlState.pageSize,
        order_by: urlState.order_by,
        filter: urlState.filter,
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

  const columns = useMemo<ColumnProps<DataBatchV2>[]>(() => {
    return [
      {
        title: '批次名称',
        dataIndex: 'name',
        key: 'name',
        width: TABLE_COL_WIDTH.NAME,
        ellipsis: true,
        render: (name: string, record: DataBatchV2) => {
          const to = isOldData
            ? `/datasets/job_detail/${datasetJobId}`
            : `/datasets/${id}/new/job_detail/${datasetJobId}/${JobDetailSubTabs.TaskList}?stageId=${record.latest_parent_dataset_job_stage_id}`;
          return <Link to={to}>{name}</Link>;
        },
      },
      {
        title: '状态',
        dataIndex: 'state',
        key: 'state',
        width: TABLE_COL_WIDTH.NORMAL,
        ...dataBatchStateFilters,
        filteredValue: expression2Filter(urlState.filter).state,
        render: (_: any, record: DataBatchV2) => {
          const { state, file_size } = record;
          const isEmptyDataset = (file_size || 0) <= 0 && state === DatasetStateFront.SUCCEEDED;
          const isErrorFileSize = record.file_size === -1;
          let type: StateTypes;
          let text: string;
          switch (state) {
            case DatasetStateFront.PENDING:
              type = 'processing';
              text = '待处理';
              break;
            case DatasetStateFront.PROCESSING:
              type = 'processing';
              text = '处理中';
              break;
            case DatasetStateFront.SUCCEEDED:
              type = 'success';
              text = '可用';
              break;
            case DatasetStateFront.DELETING:
              type = 'processing';
              text = '删除中';
              break;
            case DatasetStateFront.FAILED:
              type = 'error';
              text = '处理失败';
              break;

            default:
              type = 'default';
              text = '状态未知';
              break;
          }
          return (
            <div className="indicator-with-tip">
              <StateIndicator type={type} text={text} />
              {isEmptyDataset && !isErrorFileSize && !isInternalProcessed && (
                <Tag className={'dataset-empty-tag'} color="purple" size="small">
                  空集
                </Tag>
              )}
            </div>
          );
        },
      },
      {
        title: '文件大小',
        dataIndex: 'file_size',
        key: 'file_size',
        width: TABLE_COL_WIDTH.THIN,
        render: (_: any, record: DataBatchV2) => {
          const isErrorFileSize = record.file_size === -1;
          if (isErrorFileSize) {
            return '未知';
          }
          return <span>{isInternalProcessed ? '-' : humanFileSize(_ || 0)}</span>;
        },
      },
      {
        title: '样本量',
        dataIndex: 'num_example',
        key: 'num_example',
        width: TABLE_COL_WIDTH.THIN,
        render: (num_example: number, record: DataBatchV2) => {
          const isErrorFileSize = record.file_size === -1;
          if (isErrorFileSize) {
            return '未知';
          }
          return !isCopy || isInternalProcessed ? '-' : num_example;
        },
      },
      isDataJoin &&
        ({
          title: '求交率',
          dataIndex: 'latest_parent_dataset_job_stage_id',
          key: 'latest_parent_dataset_job_stage_id',
          width: TABLE_COL_WIDTH.ID,
          render: (latest_parent_dataset_job_stage_id: ID, record: DataBatchV2) => {
            const isErrorFileSize = record.file_size === -1;
            if (isErrorFileSize) {
              return '未知';
            }
            if (isOldData) {
              return datasetRate;
            } else {
              return (
                <DataBatchRate
                  datasetJobId={datasetJobId}
                  datasetJobStageId={latest_parent_dataset_job_stage_id}
                />
              );
            }
          },
        } as any),
      {
        title: '数据批次路径',
        dataIndex: 'path',
        key: 'path',
        width: TABLE_COL_WIDTH.NORMAL,
        render: (path: string) => (
          <Tooltip
            content={
              <Text style={{ color: '#fff' }} copyable>
                {path}
              </Text>
            }
          >
            <div className={styled.data_batch_table_path}>{path}</div>
          </Tooltip>
        ),
      },
      {
        title: '更新时间',
        dataIndex: 'updated_at',
        key: 'updated_at',
        width: TABLE_COL_WIDTH.TIME,
        sorter(a: DataBatchV2, b: DataBatchV2) {
          return a.updated_at - b.updated_at;
        },
        defaultSortOrder: getSortOrder(urlState, 'updated_at'),
        render: (date: number) => <div>{formatTimestamp(date)}</div>,
      },
      {
        title: '操作',
        dataIndex: 'state',
        key: 'operation',
        fixed: 'right',
        width: TABLE_COL_WIDTH.OPERATION,
        render: (state: DatasetStateFront, record: any) => (
          <DataBatchActions
            kindLabel={kind_label}
            data={record}
            onDelete={listQuery.refetch}
            onStop={listQuery.refetch}
            onExport={onExport}
            onRerun={onRerun}
          />
        ),
      },
    ].filter(Boolean);
  }, [
    urlState,
    listQuery.refetch,
    datasetJobId,
    isOldData,
    datasetRate,
    isDataJoin,
    isCopy,
    isInternalProcessed,
    kind_label,
    id,
  ]);

  const pagination = useMemo(() => {
    return pageTotal <= 0
      ? false
      : {
          ...paginationProps,
          total,
        };
  }, [paginationProps, pageTotal, total]);

  return (
    <>
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
          filters: Partial<Record<keyof DataBatchV2, any[]>>,
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
                    name: expression2Filter(urlState.filter).name,
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
      <ExportModal
        id={id}
        batchId={currentExportBatchId}
        visible={isShowExportModal}
        onCancel={onExportModalClose}
        onSuccess={onExportSuccess}
      />
      <DatasetBatchRerunModal
        id={id}
        batchId={currentRerunBatchId!}
        batchName={currentRerunBatchName}
        kind={kind}
        visible={isShowRerunModal}
        globalConfigs={globalConfigs}
        onCancel={onRerunModalClose}
        onSuccess={onRerunSuccess}
        onFail={onRerunModalClose}
      />
    </>
  );
  function onExport(batchId: ID) {
    setCurrentExportBatchId(batchId);
    setIsShowExportModal(true);
  }
  function onExportSuccess(datasetId: ID, datasetJobId: ID) {
    onExportModalClose();
    if (!datasetJobId && datasetJobId !== 0) {
      Message.info('导出任务ID缺失，请手动跳转「任务管理」查看详情');
    } else {
      history.push(`/datasets/${datasetId}/new/job_detail/${datasetJobId}`);
    }
  }
  function onExportModalClose() {
    setCurrentExportBatchId(undefined);
    setIsShowExportModal(false);
  }

  function onRerun(batchId: ID, batchName: string) {
    setCurrentRerunBatchId(batchId);
    setIsShowRerunModal(true);
    setCurrentRerunBatchName(batchName);
  }

  function onRerunModalClose() {
    setCurrentRerunBatchId(undefined);
    setIsShowRerunModal(false);
    setCurrentRerunBatchName('');
  }

  function onRerunSuccess() {
    onRerunModalClose();
    listQuery.refetch();
  }
};

export default DataBatchTable;
