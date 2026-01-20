import React, { FC } from 'react';
import { Link } from 'react-router-dom';
import { Table, Empty, PaginationProps, Space } from '@arco-design/web-react';
import { SorterResult } from '@arco-design/web-react/es/Table/interface';
import { formatTimestamp } from 'shared/date';
import { CONSTANTS } from 'shared/constants';

import AlgorithmType from 'components/AlgorithmType';
import MoreActions from 'components/MoreActions';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import {
  AlgorithmProject,
  AlgorithmReleaseStatus,
  EnumAlgorithmProjectSource,
} from 'typings/algorithm';
import { Participant } from 'typings/participant';
import {
  algorithmReleaseStatusFilters,
  algorithmTypeFilters,
  FILTER_ALGORITHM_MY_OPERATOR_MAPPER,
} from 'views/AlgorithmManagement/shared';
import { expression2Filter } from 'shared/filter';
import { getSortOrder } from 'views/Datasets/shared';
import { filterExpressionGenerator } from 'views/Datasets/shared';

type ColumnsGetterOptions = {
  urlState: UrlState;
  participant?: Participant[];
  onReleaseClick?: any;
  onDeleteClick?: any;
  onChangeClick?: any;
  onPublishClick?: any;
  onDownloadClick?: any;
  withoutActions?: boolean;
  isBuiltIn?: boolean;
  isParticipant?: boolean;
};

interface UrlState {
  [key: string]: any;
}

const calcStateIndicatorProps = (
  state: AlgorithmReleaseStatus,
  options: ColumnsGetterOptions,
): { type: StateTypes; text: string; tip?: string } => {
  let text = CONSTANTS.EMPTY_PLACEHOLDER;
  let type = 'default' as StateTypes;
  const tip = '';

  switch (state) {
    case AlgorithmReleaseStatus.UNRELEASED:
      text = '未发版';
      type = 'gold';
      break;
    case AlgorithmReleaseStatus.RELEASED:
      text = '已发版';
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

export const getTableColumns = (options: ColumnsGetterOptions) => {
  const cols = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
      render: (name: any, record: any) => {
        if (options.isParticipant) {
          return (
            <Link to={`/algorithm-management/detail/${record.uuid}/versions/participant`}>
              {name}
            </Link>
          );
        }
        if (options.isBuiltIn) {
          return (
            <Link to={`/algorithm-management/detail/${record.id}/files/built-in`}>{name}</Link>
          );
        }
        return <Link to={`/algorithm-management/detail/${record.id}/files/my`}>{name}</Link>;
      },
    },
    !options.isBuiltIn &&
      !options.isParticipant &&
      ({
        title: '状态',
        dataIndex: 'release_status',
        name: 'release_status',
        width: 150,
        ...algorithmReleaseStatusFilters,
        filteredValue: expression2Filter(options.urlState.filter).release_status,
        render: (state: AlgorithmReleaseStatus, record: any) => {
          return <StateIndicator {...calcStateIndicatorProps(state, options)} />;
        },
      } as any),
    {
      title: '类型',
      dataIndex: 'type',
      name: 'type',
      width: 150,
      ...algorithmTypeFilters,
      filteredValue: expression2Filter(options.urlState.filter).type,
      render(_: any, record: any) {
        return <AlgorithmType type={record.type} />;
      },
    },
    options.isParticipant && {
      title: '合作伙伴名称',
      dataIndex: 'participant_id',
      name: 'participant_id',
      width: 200,
      render(_: any, record: any) {
        let result: any = undefined;
        if (Array.isArray(options.participant) && options.participant.length !== 0) {
          result = options.participant.find((item) => item.id === record.participant_id);
        }
        return <span>{result ? result.name : '-'}</span>;
      },
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      name: 'updated_at',
      width: 200,
      sortOrder: getSortOrder(options.urlState, 'updated_at'),
      sorter(a: AlgorithmProject, b: AlgorithmProject) {
        return a.updated_at - b.updated_at;
      },
      render: (date: number) => <div>{formatTimestamp(date * 1000)}</div>,
    },
  ].filter(Boolean);

  if (!options.withoutActions) {
    cols.push({
      title: '操作',
      dataIndex: 'operation',
      name: 'operation',
      fixed: 'right',
      width: 150,
      render: (_: number, record: AlgorithmProject) => (
        <Space>
          <button
            className="custom-text-button"
            onClick={() => {
              options?.onReleaseClick?.(record);
            }}
            disabled={
              record.source !== EnumAlgorithmProjectSource.USER ||
              record.release_status === AlgorithmReleaseStatus.RELEASED
            }
          >
            {'发版'}
          </button>
          <button
            className="custom-text-button"
            onClick={() => {
              options?.onChangeClick?.(record);
            }}
          >
            编辑
          </button>
          <MoreActions
            actionList={[
              {
                label: '发布最新版本',
                disabled:
                  record.latest_version === 0 ||
                  record.source === EnumAlgorithmProjectSource.THIRD_PARTY,
                onClick() {
                  options?.onPublishClick?.(record);
                },
              },
              {
                label: '删除',
                onClick() {
                  options?.onDeleteClick?.(record);
                },
                danger: true,
              },
            ]}
          />
        </Space>
      ),
    } as any);
  }

  return cols;
};

type Props = {
  data: AlgorithmProject[];
  loading: boolean;
  isBuiltIn?: boolean;
  isParticipant?: boolean;
  noDataElement?: string;
  participant?: Participant[];
  pagination?: PaginationProps | boolean;
  urlState?: UrlState;
  setUrlState?: (newState: any) => void;
  onReleaseClick?: (record: any) => void;
  onPublishClick?: (record: any) => void;
  onChangeClick?: (record: any) => void;
  onDeleteClick?: (record: any) => void;
  onDownloadClick?: (record: any) => void;
  onShowSizeChange?: (current: number, size: number) => void;
  onPageChange?: (page: number, pageSize: number) => void;
};
const AlgorithmTable: FC<Props> = ({
  data,
  urlState = {},
  setUrlState,
  loading,
  isBuiltIn,
  isParticipant,
  participant,
  noDataElement,
  pagination,
  onReleaseClick,
  onPublishClick,
  onChangeClick,
  onDeleteClick,
  onDownloadClick,
  onPageChange,
}) => {
  return (
    <Table
      className="custom-table custom-table-left-side-filter"
      data={data}
      rowKey="uuid"
      loading={loading}
      scroll={{ x: '100%' }}
      pagination={pagination}
      noDataElement={<Empty description={noDataElement} />}
      onChange={handleChange}
      columns={getTableColumns({
        urlState,
        onReleaseClick,
        onPublishClick,
        onDeleteClick,
        onChangeClick,
        onDownloadClick,
        isBuiltIn,
        isParticipant,
        participant,
        withoutActions: isBuiltIn || isParticipant,
      })}
    />
  );

  function handleChange(
    pagination: PaginationProps,
    sorter: SorterResult,
    filters: any,
    extra: any,
  ) {
    const { action } = extra;

    switch (action) {
      case 'paginate':
        onPageChange && onPageChange(pagination.current as number, pagination.pageSize as number);
        break;
      case 'filter':
        onFilterChange && onFilterChange(filters);
        break;
      case 'sort':
        onSortChange && onSortChange(sorter);
    }
  }

  function onFilterChange(filters: any) {
    setUrlState &&
      setUrlState((prevState: any) => ({
        ...prevState,
        filter: filterExpressionGenerator(
          {
            ...filters,
            name: expression2Filter(urlState.filter).name,
          },
          FILTER_ALGORITHM_MY_OPERATOR_MAPPER,
        ),
        page: 1,
      }));
  }

  function onSortChange(sorter: SorterResult) {
    let orderValue = '';
    if (sorter.direction) {
      orderValue = sorter.direction === 'ascend' ? 'asc' : 'desc';
    }
    setUrlState &&
      setUrlState((prevState: any) => ({
        ...prevState,
        order_by: orderValue ? `${sorter.field} ${orderValue}` : '',
      }));
  }
};

export default AlgorithmTable;
