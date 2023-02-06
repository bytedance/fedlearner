import React, { useMemo } from 'react';
import { PaginationProps, Table, TableProps, Space } from '@arco-design/web-react';
import { generatePath, Link } from 'react-router-dom';
import StateIndicator from 'components/StateIndicator';
import { ModelJobAuthStatus, ModelJobState } from 'typings/modelCenter';
import { ModelJob } from 'typings/modelCenter';
import {
  ColumnsGetterOptions,
  algorithmTypeFilters,
  roleFilters,
  statusFilters,
  getModelJobStatus,
  MODEL_JOB_STATUS_MAPPER,
  resetAuthInfo,
  AUTH_STATUS_TEXT_MAP,
} from '../../shared';
import { formatTimestamp } from 'shared/date';
import MoreActions from 'components/MoreActions';
import routeMaps from '../../routes';
import { CONSTANTS } from 'shared/constants';
import AlgorithmType from 'components/AlgorithmType';
import { EnumAlgorithmProjectType } from 'typings/algorithm';
import ProgressWithText from 'components/ProgressWithText';
import { useGetCurrentProjectParticipantList, useGetCurrentPureDomainName } from 'hooks';

const staticPaginationProps: Partial<PaginationProps> = {
  pageSize: 10,
  defaultCurrent: 0,
  showTotal: true,
  sizeCanChange: false,
};

export const getTableColumns = (options: ColumnsGetterOptions) => {
  const cols = [
    {
      title: options.nameFieldText,
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (_: any, record: ModelJob) => {
        const name = record.name ? record.name : CONSTANTS.EMPTY_PLACEHOLDER;
        return (
          <Link
            to={generatePath(routeMaps.ModelEvaluationDetail, {
              id: record.id,
              module: options.module,
            })}
          >
            {name}
          </Link>
        );
      },
    },
    {
      title: '类型',
      dataIndex: 'algorithm_type',
      key: 'algorithm_type',
      width: 200,
      filteredValue: options.filterDropdownValues?.algorithm_type,
      filters: algorithmTypeFilters.filters,
      render(value: ModelJob['algorithm_type']) {
        return <AlgorithmType type={value as EnumAlgorithmProjectType} />;
      },
    },
    {
      title: '授权状态',
      dataIndex: 'auth_frontend_status',
      key: 'auth_frontend_status',
      width: 120,
      render: (value: ModelJobAuthStatus, record: any) => {
        const progressConfig = MODEL_JOB_STATUS_MAPPER?.[value];
        const authInfo = resetAuthInfo(
          record.participants_info.participants_map,
          options.participantList ?? [],
          options.myPureDomainName ?? '',
        );
        return (
          <ProgressWithText
            status={progressConfig?.status}
            statusText={progressConfig?.name}
            percent={progressConfig?.status}
            toolTipContent={
              [ModelJobAuthStatus.PART_AUTH_PENDING, ModelJobAuthStatus.SELF_AUTH_PENDING].includes(
                value,
              ) ? (
                <>
                  {authInfo.map((item: any) => (
                    <div key={item.name}>{`${item.name}: ${
                      AUTH_STATUS_TEXT_MAP?.[item.authStatus]
                    }`}</div>
                  ))}
                </>
              ) : undefined
            }
          />
        );
      },
    },
    {
      title: '运行状态',
      dataIndex: 'status',
      key: 'status',
      name: 'status',
      width: 200,
      filteredValue: options.filterDropdownValues?.status,
      filters: statusFilters.filters,
      render: (name: any, record: any) => {
        return (
          <StateIndicator
            {...getModelJobStatus(record.status, {
              ...options,
              isHideAllActionList: true,
              onLogClick: () => {
                options.onLogClick && options.onLogClick(record);
              },
              onRestartClick: () => {
                options.onRestartClick && options.onRestartClick(record);
              },
            })}
          />
        );
      },
    },
    {
      title: '创建者',
      dataIndex: 'creator_username',
      key: 'creator_username',
      name: 'creator',
      width: 200,
      render(val: string) {
        return val ?? CONSTANTS.EMPTY_PLACEHOLDER;
      },
    },
    {
      title: '发起方',
      dataIndex: 'role',
      name: 'role',
      key: 'role',
      width: 200,
      filters: roleFilters.filters,
      filterMultiple: false,
      filteredValue: options.filterDropdownValues?.role,
      render(role: string) {
        return role === 'COORDINATOR' ? '本方' : '合作伙伴';
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      name: 'created_at',
      key: 'created_at',
      width: 200,
      sorter(a: ModelJob, b: ModelJob) {
        return a.created_at - b.created_at;
      },
      render: (date: number) => <div>{formatTimestamp(date)}</div>,
    },
  ];
  if (!options.withoutActions) {
    cols.push({
      title: '操作',
      dataIndex: 'state',
      key: 'operation',
      name: 'operation',
      width: 200,
      fixed: 'right',
      render: (state: ModelJobState, record: ModelJob) => {
        const disabledTerminateOperate = state !== ModelJobState.RUNNING;
        return (
          <Space>
            <button
              className="custom-text-button"
              disabled={disabledTerminateOperate}
              onClick={() => {
                if (disabledTerminateOperate) return;
                options.onStopClick && options.onStopClick(record);
              }}
            >
              终止
            </button>
            <MoreActions
              actionList={[
                {
                  label: '删除',
                  onClick: () => {
                    options.onDeleteClick && options.onDeleteClick(record);
                  },
                  danger: true,
                },
              ]}
            />
          </Space>
        );
      },
    } as any);
  }

  return cols;
};

interface EvaluationTableProps extends Omit<TableProps, 'columns'>, ColumnsGetterOptions {}
const EvaluationTable: React.FC<EvaluationTableProps> = (props) => {
  const {
    module,
    pagination = false,
    onDeleteClick,
    onStopClick,
    nameFieldText,
    filterDropdownValues = {},
  } = props;
  const participantList = useGetCurrentProjectParticipantList();
  const myPureDomainName = useGetCurrentPureDomainName();
  const paginationProps = useMemo(() => {
    return {
      ...staticPaginationProps,
      ...(typeof pagination === 'object' ? pagination : {}),
    };
  }, [pagination]);
  return (
    <Table
      rowKey="uuid"
      className="custom-table-left-side-filter"
      scroll={{
        x: 1500,
      }}
      columns={getTableColumns({
        module,
        onDeleteClick,
        onStopClick,
        nameFieldText,
        filterDropdownValues,
        participantList,
        myPureDomainName,
      })}
      pagination={paginationProps}
      {...props}
    />
  );
};

export default EvaluationTable;
