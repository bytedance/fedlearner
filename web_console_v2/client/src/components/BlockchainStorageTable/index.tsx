import React, { useMemo } from 'react';
import GridRow from '../_base/GridRow';
import { Statistic, Table } from '@arco-design/web-react';
import { useTranslation } from 'react-i18next';
import styled from 'styled-components';
import { useQuery } from 'react-query';
import { fetchDatasetLedger } from 'services/dataset';
import { TABLE_COL_WIDTH, TIME_INTERVAL } from 'shared/constants';
import { ColumnProps } from '@arco-design/web-react/es/Table';
import {
  DatasetTransactionItem,
  DatasetTransactionStatus,
  TransactionExtraData,
} from 'typings/dataset';
import { formatTimestamp } from 'shared/date';
import { useTablePaginationWithUrlState, useUrlState } from 'hooks';
import { PaginationProps } from '@arco-design/web-react/es/Pagination/pagination';
import { SorterResult } from '@arco-design/web-react/es/Table/interface';
import { get } from 'lodash-es';
import StateIndicator from '../StateIndicator';
import { getTransactionStatus } from 'shared/dataset';

type IBlockchainStorageTable = {
  datasetId: ID;
};

const StyledStatistic = styled(Statistic)`
  margin: 12px 0;
  .arco-statistic-value {
    font-family: 'PingFang SC';
    font-style: normal;
    font-size: 16px;
    line-height: 20px;
    .arco-statistic-value-prefix {
      font-weight: 400;
    }
  }
`;

export default function BlockchainStorageTable(prop: IBlockchainStorageTable) {
  const { datasetId } = prop;
  const { t } = useTranslation();
  const { paginationProps } = useTablePaginationWithUrlState();
  const [urlState, setUrlState] = useUrlState({
    timestamp_sort: '',
  });
  const query = useQuery(['fetch_dataset_ledger', datasetId], () => fetchDatasetLedger(datasetId), {
    retry: 2,
    refetchOnWindowFocus: false,
    refetchInterval: TIME_INTERVAL.FLAG,
  });
  const totalValue = useMemo(() => {
    return get(query, 'data.data.total_value') || 0;
  }, [query]);
  const list = useMemo(() => {
    return get(query, 'data.data.transactions') || [];
  }, [query]);
  const columns = useMemo<ColumnProps<DatasetTransactionItem>[]>(() => {
    return [
      {
        title: t('dataset.col_ledger_hash'),
        dataIndex: 'trans_hash',
        key: 'trans_hash',
        width: TABLE_COL_WIDTH.NAME,
        ellipsis: true,
      },
      {
        title: t('dataset.col_ledger_block'),
        dataIndex: 'block_number',
        key: 'block_number',
        width: TABLE_COL_WIDTH.NORMAL,
      },
      {
        title: t('dataset.col_ledger_trade_block_id'),
        dataIndex: 'trans_index',
        key: 'trans_index',
        width: TABLE_COL_WIDTH.NORMAL,
      },
      {
        title: t('dataset.col_ledger_chain_time'),
        dataIndex: 'timestamp',
        key: 'timestamp',
        width: TABLE_COL_WIDTH.TIME,
        sorter(a: DatasetTransactionItem, b: DatasetTransactionItem) {
          return a.timestamp - b.timestamp;
        },
        defaultSortOrder: urlState?.timestamp_sort,
        render: (date: number) => <div>{formatTimestamp(date)}</div>,
      },
      {
        title: t('dataset.col_ledger_sender'),
        dataIndex: 'sender_name',
        key: 'sender_name',
        width: TABLE_COL_WIDTH.NORMAL,
      },
      {
        title: t('dataset.col_ledger_receiver'),
        dataIndex: 'receiver_name',
        key: 'receiver_name',
        width: TABLE_COL_WIDTH.OPERATION,
      },
      {
        title: t('dataset.col_ledger_trade_fee'),
        dataIndex: 'value',
        key: 'value',
        width: TABLE_COL_WIDTH.NORMAL,
      },
      {
        title: t('dataset.col_ledger_trade_status'),
        dataIndex: 'status',
        key: 'status',
        width: TABLE_COL_WIDTH.NORMAL,
        render: (val: DatasetTransactionStatus) => {
          return <StateIndicator {...getTransactionStatus(val)} />;
        },
      },
      {
        title: t('dataset.col_ledger_trade_info'),
        dataIndex: 'extra_data',
        key: 'extra_data',
        width: TABLE_COL_WIDTH.BIG_WIDTH,
        ellipsis: true,
        render: (val: TransactionExtraData) => {
          return val?.transaction_info;
        },
      },
    ];
  }, [t, urlState]);
  const handleOnChange = (
    pagination: PaginationProps,
    sorter: SorterResult,
    filters: Partial<Record<keyof DatasetTransactionItem, string[]>>,
    extra: {
      currentData: DatasetTransactionItem[];
      action: 'paginate' | 'sort' | 'filter';
    },
  ) => {
    switch (extra.action) {
      case 'sort':
        setUrlState((prevState) => ({
          ...prevState,
          [`${sorter.field}_sort`]: sorter.direction,
        }));
        break;
      default:
        break;
    }
  };
  return (
    <>
      <GridRow>
        <StyledStatistic
          groupSeparator={true}
          value={totalValue}
          prefix={t('dataset.label_current_dataset_value')}
        />
      </GridRow>
      <Table
        rowKey="trans_hash"
        loading={query.isFetching}
        pagination={{
          ...paginationProps,
          sizeCanChange: true,
        }}
        data={list}
        columns={columns}
        onChange={handleOnChange}
      />
    </>
  );
}
