import React, { FC } from 'react';

import { formatTimestamp } from 'shared/date';
import { modelDirectionTypeToTextMap, getDotState, modelServingStateToTextMap } from './shared';

import Table from 'components/Table';
import MoreActions from 'components/MoreActions';
import StateIndicator from 'components/StateIndicator';

import { Tag } from '@arco-design/web-react';
import { ModelServing, ModelDirectionType, ModelServingState } from 'typings/modelServing';

import { TableColumnProps, TableProps, Space } from '@arco-design/web-react';
import { SorterResult, SortDirection } from '@arco-design/web-react/es/Table/interface';

import styles from './ModelServingTable.module.less';

type FilterValue = string[];

type ColumnsGetterOptions = {
  filter?: Record<string, FilterValue>;
  sorter?: Record<string, SortDirection>;
  onScaleClick?: any;
  onDeleteClick?: any;
  onEditClick?: any;
};

const getTableColumns = (options: ColumnsGetterOptions) => {
  const cols: TableColumnProps[] = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
      render: (name) => {
        return <span className={styles.edit_text_container}>{name}</span>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      filterMultiple: false,
      filteredValue: options?.filter?.status || [],
      filters: [
        {
          text: modelServingStateToTextMap.AVAILABLE,
          value: ModelServingState.AVAILABLE,
        },
        {
          text: modelServingStateToTextMap.LOADING,
          value: ModelServingState.LOADING,
        },
        {
          text: modelServingStateToTextMap.UNKNOWN,
          value: ModelServingState.UNKNOWN,
        },
        {
          text: modelServingStateToTextMap.UNLOADING,
          value: ModelServingState.UNLOADING,
        },
        {
          text: modelServingStateToTextMap.PENDING_ACCEPT,
          value: ModelServingState.PENDING_ACCEPT,
        },
      ],
      render: (_, record) => {
        return <StateIndicator {...getDotState(record)} />;
      },
    },
    {
      title: '模型类型',
      dataIndex: 'is_local',
      key: 'is_local',
      width: 150,
      filteredValue: options?.filter?.is_local || [],
      filters: [
        {
          text: modelDirectionTypeToTextMap.horizontal,
          value: 'true',
        },
        {
          text: modelDirectionTypeToTextMap.vertical,
          value: 'false',
        },
      ],
      filterMultiple: false,
      render: (type: boolean) => {
        const modelType = type ? ModelDirectionType.HORIZONTAL : ModelDirectionType.VERTICAL;
        return (
          <Tag
            className={styles.tag_container}
            style={{
              background:
                modelType === ModelDirectionType.HORIZONTAL
                  ? 'rgb(var(--orange-1))'
                  : 'rgb(var(--blue-1))',
            }}
          >
            {modelDirectionTypeToTextMap[modelType]}
          </Tag>
        );
      },
    },
    {
      title: '实例数量',
      dataIndex: 'instance_num_status',
      key: 'instance_num_status',
      width: 100,
      render: (value) => value || '-',
    },
    {
      title: '调用权限',
      dataIndex: 'support_inference',
      key: 'support_inference',
      width: 100,
      render(val: boolean) {
        return (
          <Tag style={{ background: val ? 'rgb(var(--green-1))' : 'rgb(var(--gray-2))' }}>
            {val ? '可调用' : '不可调用'}
          </Tag>
        );
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 200,
      sorter: true,
      sortOrder: options.sorter?.created_at || undefined,
      render: (date: number) => formatTimestamp(date),
    },
    {
      title: '操作',
      dataIndex: 'operation',
      key: 'operation',
      fixed: 'right',
      width: 120,
      render: (_, record) => {
        const isDisabled =
          record.status !== ModelServingState.AVAILABLE || record.resource === undefined;
        //TODO:等后端支持手动更新模型
        // const editIsDisabled = ![ModelServingState.AVAILABLE, ModelServingState.LOADING].includes(
        //   record.status,
        // );

        return (
          <Space>
            <span
              className={styles.edit_text_container}
              data-is-disabled={isDisabled}
              onClick={(event) => {
                event.stopPropagation();
                if (!isDisabled) {
                  options?.onScaleClick(record);
                }
              }}
            >
              扩缩容
            </span>
            <MoreActions
              actionList={[
                {
                  label: '编辑',
                  //TODO:等后端支持手动更新模型
                  //disabled: editIsDisabled,
                  onClick: () => {
                    options?.onEditClick(record);
                  },
                },
                {
                  label: '删除',
                  onClick: () => {
                    options?.onDeleteClick(record);
                  },
                  danger: true,
                },
              ]}
            />
          </Space>
        );
      },
    },
  ];

  return cols;
};

interface Props extends TableProps<ModelServing> {
  total?: number;
  loading: boolean;
  dataSource: any[];
  filter?: Record<string, FilterValue>;
  sorter?: Record<string, SortDirection>;
  onRowClick?: (record: ModelServing) => void;
  onEditClick?: (record: ModelServing) => void;
  onScaleClick?: (record: ModelServing) => void;
  onDeleteClick?: (record: ModelServing) => void;
  onShowSizeChange?: (current: number, size: number) => void;
  onPageChange?: (page: number, pageSize: number) => void;
  onSortChange?: (sorter: SorterResult) => void;
  onFilterChange?: (filter: Record<string, any>) => void;
}

const ModelServingTable: FC<Props> = ({
  total,
  loading,
  filter,
  sorter,
  dataSource,
  onRowClick,
  onEditClick,
  onScaleClick,
  onDeleteClick,
  onShowSizeChange,
  onPageChange,
  onSortChange,
  onFilterChange,
  ...restProps
}) => {
  return (
    <>
      <Table<ModelServing>
        className="customFilterIconTable"
        rowKey="id"
        scroll={{ x: '100%' }}
        loading={loading}
        total={total}
        data={dataSource}
        columns={getTableColumns({
          filter,
          sorter,
          onEditClick,
          onScaleClick,
          onDeleteClick,
        })}
        onChange={(pagination, sorter, filters, extra) => {
          const { action } = extra;

          switch (action) {
            case 'paginate':
              onShowSizeChange?.(pagination.current as number, pagination.pageSize as number);
              break;
            case 'sort':
              onSortChange?.(sorter as SorterResult);
              break;
            case 'filter':
              onFilterChange?.(filters);
              break;
            default:
          }
        }}
        onShowSizeChange={onShowSizeChange}
        onPageChange={onPageChange}
        onRow={(record) => ({
          onClick: () => {
            onRowClick?.(record);
          },
        })}
        {...restProps}
      />
    </>
  );
};

export default ModelServingTable;
