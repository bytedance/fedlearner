import React, { FC } from 'react';

import { formatTimestamp } from 'shared/date';

import Table from 'components/Table';
import StateIndicator, { StateTypes, ActionItem } from 'components/StateIndicator';

import { TableProps, TableColumnProps } from '@arco-design/web-react';
import { ModelServingInstance, ModelServingInstanceState } from 'typings/modelServing';
import { SortDirection } from '@arco-design/web-react/es/Table/interface';

import styles from './InstanceTable.module.less';

type FilterValue = string[];
type ColumnsGetterOptions = {
  filter?: Record<string, FilterValue>;
  sorter?: Record<string, SortDirection>;
  onLogClick?: any;
};

function getDotState(
  instance: ModelServingInstance,
  options: ColumnsGetterOptions,
): { type: StateTypes; text: string; tip?: string; actionList?: ActionItem[] } {
  if (instance.status === ModelServingInstanceState.AVAILABLE) {
    return {
      text: '运行中',
      type: 'success',
    };
  }
  if (instance.status === ModelServingInstanceState.UNAVAILABLE) {
    return {
      text: '异常',
      type: 'error',
      // TODO: error tips
    };
  }

  return {
    text: '异常',
    type: 'error',
  };
}

const getTableColumns = (options: ColumnsGetterOptions) => {
  const cols: TableColumnProps[] = [
    {
      key: 'name',
      dataIndex: 'name',
      title: '实例ID',
      width: 320,
    },
    {
      key: 'instances_status',
      dataIndex: 'status',
      filterMultiple: false,
      filteredValue: options?.filter?.instances_status,
      filters: [
        { text: '运行中', value: ModelServingInstanceState.AVAILABLE },
        {
          text: '异常',
          value: ModelServingInstanceState.UNAVAILABLE,
        },
      ],
      onFilter: (value, record) => record.status === value,
      title: '状态',
      render: (_: any, record: any) => {
        return (
          <StateIndicator
            {...getDotState(record, {
              ...options,
            })}
          />
        );
      },
    },
    // Because BE can't get cpu/memory info, so hide temporarily
    // {
    //   title: i18n.t('model_serving.col_cpu'),
    //   dataIndex: 'cpu',
    //   key: 'cpu',
    //   render: (value, record) => {
    //     const percent = parseFloat(value) || 0;
    //     return <Progress percent={percent} size="small" format={(percent) => `${percent || 0}%`} />;
    //   },
    // },
    // {
    //   title: i18n.t('model_serving.col_men'),
    //   dataIndex: 'memory',
    //   key: 'memory',
    //   render: (value, record) => {
    //     const percent = parseFloat(value) || 0;
    //     return <Progress percent={percent} size="small" format={(percent) => `${percent || 0}%`} />;
    //   },
    // },
    {
      key: 'created_at',
      dataIndex: 'created_at',
      title: '创建时间',
      sorter: true,
      sortOrder: options.sorter?.created_at,
      render: (date: number) => <div>{formatTimestamp(date)}</div>,
    },
    {
      key: 'operation',
      dataIndex: 'operation',
      title: '操作',
      fixed: 'right',
      render: (_, record) => {
        const isDisabled = false;

        return (
          <>
            <span
              className={styles.edit_text_container}
              data-is-disabled={isDisabled}
              onClick={(event) => {
                event.stopPropagation();
                options?.onLogClick(record);
              }}
            >
              查看日志
            </span>
          </>
        );
      },
    },
  ];

  return cols;
};

interface Props extends TableProps<ModelServingInstance> {
  loading: boolean;
  filter?: Record<string, FilterValue>;
  sorter?: Record<string, SortDirection>;
  dataSource: any[];
  total?: number;
  onLogClick?: (record: ModelServingInstance) => void;
  onShowSizeChange?: (current: number, size: number) => void;
  onPageChange?: (page: number, pageSize: number) => void;
}

const InstanceTable: FC<Props> = ({
  loading,
  dataSource,
  total,
  filter,
  sorter,
  onLogClick,
  onShowSizeChange,
  onPageChange,
  ...restProps
}) => {
  return (
    <Table
      className="customFilterIconTable"
      rowKey="name"
      scroll={{ x: '100%' }}
      loading={loading}
      total={total}
      data={dataSource}
      columns={getTableColumns({
        filter,
        sorter,
        onLogClick,
      })}
      onShowSizeChange={onShowSizeChange}
      onPageChange={onPageChange}
      pagination={{ hideOnSinglePage: true }}
      {...restProps}
    />
  );
};

export default InstanceTable;
