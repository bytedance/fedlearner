import React, { FC, useMemo } from 'react';
import { generatePath, useHistory } from 'react-router';
import { useMutation, useQueries, useQuery } from 'react-query';

import {
  useGetAppFlagValue,
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantId,
  useGetCurrentProjectParticipantList,
  useGetCurrentPureDomainName,
  useTablePaginationWithUrlState,
  useUrlState,
} from 'hooks';
import {
  fetchModelJobGroupList,
  deleteModelJobGroup,
  authorizeModelJobGroup,
  fetchPeerModelJobGroupDetail,
  fetchModelJobGroupDetail,
} from 'services/modelCenter';
import { TIME_INTERVAL, CONSTANTS } from 'shared/constants';
import { formatTimestamp } from 'shared/date';
import { expression2Filter } from 'shared/filter';
import { filterExpressionGenerator } from 'views/Datasets/shared';
import {
  algorithmTypeFilters,
  roleFilters,
  statusFilters,
  FILTER_MODEL_TRAIN_OPERATOR_MAPPER,
  MODEL_GROUP_STATUS_MAPPER,
  resetAuthInfo,
  AUTH_STATUS_TEXT_MAP,
  getModelJobStatus,
} from 'views/ModelCenter/shared';
import { launchModelJobGroup } from 'services/modelCenter';

import { Link } from 'react-router-dom';
import { Button, Input, Message, Space, Table } from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import GridRow from 'components/_base/GridRow';
import SharedPageLayout from 'components/SharedPageLayout';
import MoreActions from 'components/MoreActions';
import TodoPopover from 'components/TodoPopover';
import Modal from 'components/Modal';

import { ColumnProps } from '@arco-design/web-react/es/Table';
import { ModelGroupStatus, ModelJobGroup, ModelJobRole } from 'typings/modelCenter';

import routes from '../../routes';
import StateIndicator from 'components/StateIndicator';
import ButtonWithPopconfirm from 'components/ButtonWithPopconfirm';
import AlgorithmType from 'components/AlgorithmType';
import { EnumAlgorithmProjectType } from 'typings/algorithm';
import ProgressWithText from 'components/ProgressWithText';
import { Flag, FlagKey } from 'typings/flag';
import { fetchParticipantFlagById } from 'services/flag';

type TProps = {};
const { Search } = Input;
const List: FC<TProps> = function (props: TProps) {
  const history = useHistory();
  const { urlState: pageInfoState, paginationProps } = useTablePaginationWithUrlState();
  const [urlState, setUrlState] = useUrlState({
    //TODO: BE support states filter & sort
    states: [],
    updated_at_sort: '',
    filter: filterExpressionGenerator(
      {
        configured: true,
      },
      FILTER_MODEL_TRAIN_OPERATOR_MAPPER,
    ),
  });

  const projectId = useGetCurrentProjectId();
  const participantId = useGetCurrentProjectParticipantId();
  const participantList = useGetCurrentProjectParticipantList();
  const model_job_global_config_enabled = useGetAppFlagValue(
    FlagKey.MODEL_JOB_GLOBAL_CONFIG_ENABLED,
  );
  const myPureDomainName = useGetCurrentPureDomainName();

  const participantsFlagQueries = useQueries(
    participantList.map((participant) => {
      return {
        queryKey: ['fetchParticipantFlag', participant.id],
        queryFn: () => fetchParticipantFlagById(participant.id),
        retry: 2,
        enabled: Boolean(participant.id),
        refetchOnWindowFocus: false,
      };
    }),
  );

  const listQuery = useQuery(
    ['fetchModelJobGroupList', projectId, pageInfoState.page, pageInfoState.pageSize, urlState],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return;
      }
      return fetchModelJobGroupList(projectId!, {
        page: pageInfoState.page,
        pageSize: pageInfoState.pageSize,
        filter: urlState.filter,
      });
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST,
      keepPreviousData: true,
      refetchOnWindowFocus: false,
    },
  );

  const authorizeMutate = useMutation(
    (payload: { id: ID; authorized: boolean }) => {
      return authorizeModelJobGroup(projectId!, payload.id, payload.authorized);
    },
    {
      onSuccess(_, { authorized }) {
        listQuery.refetch();
        Message.success(!authorized ? '撤销成功' : '授权成功');
      },
      onError(_, { authorized }) {
        listQuery.refetch();
        Message.error(!authorized ? '撤销失败' : '授权失败');
      },
    },
  );
  const linkToNewCreatePage = useMemo(() => {
    let flag = true;
    participantsFlagQueries.forEach((item) => {
      const participantFlag = item.data as { data: Flag } | undefined;
      if (participantFlag?.data.model_job_global_config_enabled === false) {
        flag = false;
      }
    });
    return flag;
  }, [participantsFlagQueries]);

  const list = useMemo(() => {
    if (!listQuery.data?.data) return [];
    return listQuery.data.data;
  }, [listQuery.data]);

  const columns = useMemo<ColumnProps<ModelJobGroup>[]>(() => {
    return [
      {
        title: '名称',
        dataIndex: 'name',
        key: 'name',
        width: 200,
        ellipsis: true,
        render: (name: string, record) => {
          return (
            <Link
              to={generatePath(routes.ModelTrainDetail, {
                id: record.id,
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
        name: 'algorithm_type',
        width: 150,
        filters: algorithmTypeFilters.filters,
        filteredValue: expression2Filter(urlState.filter)?.algorithm_type,
        render: (type) => {
          return <AlgorithmType type={type as EnumAlgorithmProjectType} />;
        },
      },
      {
        title: '发起方',
        dataIndex: 'role',
        name: 'role',
        width: 120,
        filters: roleFilters.filters,
        filteredValue: expression2Filter(urlState.filter)?.role,
        filterMultiple: false,
        render: (role: string, record) =>
          role
            ? role === ModelJobRole.COORDINATOR
              ? '我方'
              : participantList.find((item) => item.id === record.coordinator_id)?.name ||
                CONSTANTS.EMPTY_PLACEHOLDER
            : CONSTANTS.EMPTY_PLACEHOLDER,
      },
      {
        title: '授权状态',
        dataIndex: 'auth_frontend_status',
        name: 'auth_frontend_status',
        width: 120,
        render: (value: ModelGroupStatus, record: any) => {
          const progressConfig = MODEL_GROUP_STATUS_MAPPER?.[value];
          const authInfo = resetAuthInfo(
            record.participants_info.participants_map,
            participantList,
            myPureDomainName,
          );
          return (
            <ProgressWithText
              statusText={progressConfig?.name}
              status={progressConfig?.status}
              percent={progressConfig?.percent}
              toolTipContent={
                [ModelGroupStatus.PART_AUTH_PENDING, ModelGroupStatus.SELF_AUTH_PENDING].includes(
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
        title: '任务总数',
        dataIndex: 'latest_version',
        name: 'model_jobs',
        width: 100,
        align: 'center',
        render: (value: any) => {
          return typeof value === 'number' ? value : CONSTANTS.EMPTY_PLACEHOLDER;
        },
      },
      {
        title: '最新任务状态',
        dataIndex: 'latest_job_state',
        name: 'latest_job_state',
        width: 150,
        // TODO: 后端筛选
        ...statusFilters,
        filteredValue: urlState.states ?? [],
        render: (value: any, record) => {
          if (!value) {
            return CONSTANTS.EMPTY_PLACEHOLDER;
          }
          return (
            <StateIndicator
              {...getModelJobStatus(record.latest_job_state, {
                isHideAllActionList: true,
              })}
            />
          );
        },
      },
      {
        title: '创建者',
        dataIndex: 'creator_username',
        name: 'creator',
        width: 120,
        render: (value: any) => value ?? CONSTANTS.EMPTY_PLACEHOLDER,
      },
      {
        title: '更新时间',
        dataIndex: 'updated_at',
        name: 'updated_at',
        width: 150,
        sorter(a: ModelJobGroup, b: ModelJobGroup) {
          return a.created_at - b.created_at;
        },
        defaultSortOrder: urlState?.updated_at_sort,
        render: (date: number) => <div>{formatTimestamp(date)}</div>,
      },
      {
        title: '操作',
        dataIndex: 'authorized',
        name: 'operation',
        fixed: 'right',
        key: 'operate',
        width: 200,
        render: (authorized: boolean, record) => (
          <Space>
            <button
              className="custom-text-button"
              style={{
                width: 60,
                textAlign: 'left',
              }}
              onClick={async () => {
                let isPeerAuthorized = false;
                let isOldModelGroup = true;
                try {
                  const res = await fetchModelJobGroupDetail(projectId!, record.id!);
                  const detail = res.data;
                  isOldModelGroup = Boolean(detail?.config?.job_definitions?.length);
                } catch (error: any) {
                  Message.error(error.message);
                }
                if (isOldModelGroup && record.role !== 'COORDINATOR') {
                  Message.info('旧版模型训练作业非发起方暂不支持发起模型训练任务');
                  return;
                }
                try {
                  // TODO:能否发起训练任务判定逻辑后续根据 auth_frontend_status 字段判断
                  const resp = await fetchPeerModelJobGroupDetail(
                    projectId!,
                    record.id!,
                    participantId!,
                  );
                  isPeerAuthorized = resp?.data?.authorized ?? false;
                } catch (error: any) {
                  Message.error(error.message);
                }

                if (!isPeerAuthorized) {
                  Message.info('合作伙伴未授权，不能发起新任务');
                  return;
                }

                model_job_global_config_enabled && !isOldModelGroup
                  ? history.push(
                      generatePath(routes.ModelTrainJobCreate, {
                        type: 'once',
                        id: record?.id,
                        step: 'coordinator',
                      }),
                    )
                  : launchModelJobGroup(projectId!, record.id)
                      .then((resp) => {
                        Message.success('发起成功');
                        listQuery.refetch();
                      })
                      .catch((error) => Message.error(error.message));
              }}
            >
              发起新任务
            </button>

            <ButtonWithPopconfirm
              title={
                record.authorized
                  ? '撤销授权后，发起方不可运行模型训练，正在运行的任务不受影响'
                  : '授权后，发起方可以运行模型训练'
              }
              buttonProps={{
                type: 'text',
                className: 'custom-text-button',
                style: {
                  width: 60,
                  textAlign: 'left',
                },
              }}
              buttonText={record.authorized ? '撤销' : '授权'}
              onConfirm={() => {
                authorizeMutate.mutate({
                  id: record.id,
                  authorized: !record.authorized,
                });
              }}
            />

            <MoreActions
              actionList={[
                {
                  label: '删除' as any,
                  danger: true,
                  onClick() {
                    Modal.delete({
                      title: `确认要删除「${record.name}」？`,
                      content: '删除后，该模型训练下的所有信息无法复原，请谨慎操作',
                      onOk() {
                        deleteModelJobGroup(projectId!, record.id)
                          .then((resp) => {
                            Message.success('删除成功');
                            listQuery.refetch();
                          })
                          .catch((error) => Message.error(error.message));
                      },
                    });
                  },
                },
              ]}
            />
          </Space>
        ),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlState, projectId, participantId, myPureDomainName, participantList]);

  return (
    <SharedPageLayout title={'模型训练'} rightTitle={<TodoPopover.NewTrainModel />}>
      <GridRow justify="space-between" align="center">
        <Button
          type="primary"
          className={'custom-operation-button'}
          icon={<IconPlus />}
          onClick={goToCreatePage}
        >
          创建训练
        </Button>
        <Search
          className={'custom-input'}
          allowClear
          placeholder={'输入模型训练名称'}
          defaultValue={expression2Filter(urlState.filter).name}
          onSearch={onSearch}
          onClear={() => onSearch('')}
        />
      </GridRow>
      <Table
        className="custom-table custom-table-left-side-filter"
        rowKey="id"
        loading={listQuery.isFetching}
        data={list}
        scroll={{ x: '100%' }}
        columns={columns}
        pagination={{
          ...paginationProps,
          total: listQuery.data?.page_meta?.total_items ?? undefined,
        }}
        onChange={(pagination, sorter, filters, extra) => {
          switch (extra.action) {
            case 'sort':
              //TODO: BE support sort
              setUrlState((prevState) => ({
                ...prevState,
                [`${sorter.field}_sort`]: sorter.direction,
              }));
              break;
            case 'filter': {
              const copyFilters = {
                ...filters,
                name: expression2Filter(urlState.filter).name,
                configured: true,
              };
              setUrlState((prevState) => ({
                ...prevState,
                page: 1,
                filter: filterExpressionGenerator(copyFilters, FILTER_MODEL_TRAIN_OPERATOR_MAPPER),
                states: filters.latest_job_state,
              }));
              break;
            }
            default:
          }
        }}
      />
    </SharedPageLayout>
  );

  function goToCreatePage() {
    model_job_global_config_enabled && linkToNewCreatePage
      ? history.push(generatePath(routes.ModelTrainCreateCentralization, { role: 'sender' }))
      : history.push(
          generatePath(routes.ModelTrainCreate, {
            role: 'sender',
            action: 'create',
          }),
        );
  }

  function onSearch(value: string) {
    const filters = expression2Filter(urlState.filter);
    filters.name = value;
    setUrlState((prevState) => ({
      ...prevState,
      keyword: value,
      page: 1,
      filter: filterExpressionGenerator(filters, FILTER_MODEL_TRAIN_OPERATOR_MAPPER),
    }));
  }
};

export default List;
