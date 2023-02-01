import React, { FC, useMemo, useState } from 'react';
import { generatePath, useHistory, useParams, Link } from 'react-router-dom';
import { useMutation, useQuery } from 'react-query';
import dayjs from 'dayjs';

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
  authorizeModelJobGroup,
  deleteModelJobGroup,
  fetchModelJobGroupDetail,
  fetchPeerModelJobGroupDetail,
  launchModelJobGroup,
  stopModelJob,
  fetchModelJobList_new,
  stopAutoUpdateModelJob,
  fetchAutoUpdateModelJobDetail,
} from 'services/modelCenter';
import { fetchDatasetDetail, fetchDatasetJobDetail } from 'services/dataset';
import { formatTimestamp } from 'shared/date';
import {
  Avatar,
  AUTH_STATUS_TEXT_MAP,
  getConfigInitialValues,
  getModelJobStatus,
  isNNAlgorithm,
  isVerticalNNAlgorithm,
  MODEL_GROUP_STATUS_MAPPER,
  resetAuthInfo,
  statusFilters,
  FILTER_MODEL_JOB_OPERATOR_MAPPER,
  isTreeAlgorithm,
} from 'views/ModelCenter/shared';
import { CONSTANTS } from 'shared/constants';

import {
  Grid,
  Button,
  Space,
  Tag,
  Message,
  Table,
  Spin,
  Tooltip,
  Popover,
} from '@arco-design/web-react';
import BackButton from 'components/BackButton';
import MoreActions from 'components/MoreActions';
import PropertyList from 'components/PropertyList';
import SharedPageLayout from 'components/SharedPageLayout';
import ModelJobDetailDrawer from '../../ModelJobDetailDrawer';

import routes from '../../routes';
import { EnumAlgorithmProjectType } from 'typings/algorithm';
import { LabelStrong } from 'styles/elements';
import { ColumnProps } from '@arco-design/web-react/es/Table';
import {
  AutoModelJobStatus,
  ModelGroupStatus,
  ModelJob,
  ModelJobRole,
  ModelJobStatus,
} from 'typings/modelCenter';
import { DatasetKindBackEndType, DatasetType__archived } from 'typings/dataset';
import StateIndicator from 'components/StateIndicator';
import { WorkflowState } from 'typings/workflow';
import CountTime from 'components/CountTime';
import Modal from 'components/Modal';
import AlgorithmType from 'components/AlgorithmType';
import { IconCheckCircleFill, IconExclamationCircleFill } from '@arco-design/web-react/icon';
import TrainJobCompareModal from '../../TrainJobCompareModal';
import WhichAlgorithm from 'components/WhichAlgorithm';

import styles from './index.module.less';
import ProgressWithText from 'components/ProgressWithText';
import { FlagKey } from 'typings/flag';
import { filterExpressionGenerator } from 'views/Datasets/shared';
import { expression2Filter } from 'shared/filter';
import AlgorithmProjectSelect from '../CreateCentralization/AlgorithmProjectSelect';

const { Row, Col } = Grid;

type TRouteParams = {
  id: string;
};
const AUTO_STATUS_TEXT_MAPPER: Record<AutoModelJobStatus, string> = {
  [AutoModelJobStatus.INITIAL]: '发起定时续训任务',
  [AutoModelJobStatus.ACTIVE]: '停止定时续训任务',
  [AutoModelJobStatus.STOPPED]: '配置定时续训任务',
};

const Detail: FC = () => {
  const history = useHistory();
  const params = useParams<TRouteParams>();
  const [autoBtnLoading, setAutoBtnLoading] = useState<boolean>(false);
  const { urlState: pageInfoState, paginationProps } = useTablePaginationWithUrlState();
  const [urlState, setUrlState] = useUrlState<{
    filter?: string;
    page?: number;
    pageSize?: number;
  }>({});
  const projectId = useGetCurrentProjectId();
  const participantId = useGetCurrentProjectParticipantId();
  const participantList = useGetCurrentProjectParticipantList();
  const myPureDomainName = useGetCurrentPureDomainName();

  const model_job_global_config_enabled = useGetAppFlagValue(
    FlagKey.MODEL_JOB_GLOBAL_CONFIG_ENABLED,
  );

  const queryKeys = ['modelJobDetail', params.id, projectId];

  const detailQuery = useQuery(
    queryKeys,
    () => {
      return fetchModelJobGroupDetail(projectId!, params.id);
    },
    {
      enabled: Boolean(projectId) && Boolean(params.id),
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const modelJobListQuery = useQuery(
    [
      'fetchModelJobListQuery',
      projectId,
      params.id,
      pageInfoState.page,
      pageInfoState.pageSize,
      urlState.filter,
    ],
    () =>
      fetchModelJobList_new(projectId!, {
        project_id: projectId as string,
        group_id: params.id,
        page: pageInfoState.page,
        page_size: pageInfoState.pageSize,
        filter: urlState.filter || undefined,
      }),
    {
      enabled: Boolean(projectId) && Boolean(params.id),
      retry: 2,
      refetchOnWindowFocus: false,
      keepPreviousData: true,
    },
  );

  const datasetDetailQuery = useQuery(
    ['datasetDetailQuery', detailQuery.data?.data?.dataset_id],
    () => {
      return fetchDatasetDetail(detailQuery.data?.data?.dataset_id);
    },
    {
      enabled: detailQuery.data?.data?.dataset_id !== undefined,
    },
  );

  const authorizeMutate = useMutation(
    (payload: { id: ID; authorized: boolean }) => {
      return authorizeModelJobGroup(projectId!, payload.id, payload.authorized);
    },
    {
      onSuccess(_, { authorized }) {
        detailQuery.refetch();
        Message.success(!authorized ? '撤销成功' : '授权成功');
      },
      onError(_, { authorized }) {
        detailQuery.refetch();
        Message.error(!authorized ? '撤销失败' : '授权失败');
      },
    },
  );

  const detail = useMemo(() => detailQuery.data?.data, [detailQuery]);
  const modelJobList = useMemo(() => modelJobListQuery.data?.data, [modelJobListQuery]);
  const datasetDetail = useMemo(() => datasetDetailQuery.data?.data, [datasetDetailQuery]);

  const datasetJobQuery = useQuery(
    [
      'fetchDatasetJobDetail',
      projectId,
      datasetDetail?.parent_dataset_job_id,
      datasetDetail?.dataset_type,
    ],
    () => fetchDatasetJobDetail(projectId!, datasetDetail?.parent_dataset_job_id!),
    {
      refetchOnWindowFocus: false,
      retry: 2,
      enabled:
        Boolean(projectId && datasetDetail?.parent_dataset_job_id) &&
        datasetDetail?.dataset_type === DatasetType__archived.STREAMING,
    },
  );

  const datasetJob = useMemo(() => datasetJobQuery.data?.data, [datasetJobQuery]);

  const isOldModelGroup = useMemo(() => {
    return Boolean(detail?.config?.job_definitions?.length);
  }, [detail?.config?.job_definitions?.length]);
  const progressConfig = useMemo(() => {
    if (!detail?.auth_frontend_status) {
      return undefined;
    }
    return MODEL_GROUP_STATUS_MAPPER?.[detail.auth_frontend_status];
  }, [detail]);

  const displayedProps = useMemo(
    () => {
      const { loss_type, algorithm } = getConfigInitialValues(detail?.config!, [
        'loss_type',
        'algorithm',
      ]);
      let algorithmValue = {
        algorithmId: undefined,
        algorithmUuid: undefined,
        participantId: undefined,
      };
      try {
        algorithmValue = JSON.parse(algorithm);
      } catch (e) {}
      const { algorithmId, algorithmUuid, participantId } = algorithmValue;
      const { name, status, percent } = progressConfig ?? {};
      const authInfo = resetAuthInfo(
        detail?.participants_info?.participants_map,
        participantList,
        myPureDomainName,
      );
      return [
        {
          value: detail?.role
            ? detail.role === ModelJobRole.COORDINATOR
              ? '我方'
              : participantList.find((item) => item.id === detail.coordinator_id)?.name ||
                CONSTANTS.EMPTY_PLACEHOLDER
            : CONSTANTS.EMPTY_PLACEHOLDER,
          label: '发起方',
        },
        {
          label: '授权状态',
          value: (
            <ProgressWithText
              className={styles.model_progress_container}
              statusText={name}
              status={status}
              percent={percent}
              toolTipContent={
                detail?.auth_frontend_status &&
                [ModelGroupStatus.PART_AUTH_PENDING, ModelGroupStatus.SELF_AUTH_PENDING].includes(
                  detail?.auth_frontend_status,
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
          ),
        },
        {
          value: detail?.creator_username ?? CONSTANTS.EMPTY_PLACEHOLDER,
          label: '创建者',
        },
        {
          value:
            datasetDetail?.dataset_kind === DatasetKindBackEndType.PROCESSED ? (
              <Link
                to={`/datasets/${DatasetKindBackEndType.PROCESSED.toLowerCase()}/detail/${
                  detail?.dataset_id
                }/dataset_job_detail`}
              >
                {datasetDetail?.name}
              </Link>
            ) : (
              CONSTANTS.EMPTY_PLACEHOLDER
            ),
          label: '数据集',
        },
        detail?.algorithm_type && isNNAlgorithm(detail?.algorithm_type as EnumAlgorithmProjectType)
          ? {
              value: (
                <WhichAlgorithm
                  id={algorithmId!}
                  uuid={algorithmUuid}
                  participantId={participantId}
                  formatter={(algorithm: Algorithm) => algorithm.name}
                />
              ),
              label: '算法',
            }
          : { value: loss_type, label: '损失类型' },
        {
          value: detail?.updated_at
            ? formatTimestamp(detail.updated_at)
            : CONSTANTS.EMPTY_PLACEHOLDER,
          label: '更新时间',
        },
        {
          value: detail?.created_at
            ? formatTimestamp(detail.created_at)
            : CONSTANTS.EMPTY_PLACEHOLDER,
          label: '创建时间',
        },
      ];
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [detail, datasetDetailQuery, participantList, progressConfig, myPureDomainName],
  );

  const displayedProps_new = useMemo(() => {
    const { name, status, percent } = progressConfig ?? {};
    const authInfo = resetAuthInfo(
      detail?.participants_info?.participants_map,
      participantList,
      myPureDomainName,
    );
    const keyList = Object.keys(detail?.algorithm_project_uuid_list?.algorithm_projects ?? {});
    const textList = keyList
      .map((item) => {
        return {
          name: item,
          algorithmProjectUuid: detail?.algorithm_project_uuid_list?.algorithm_projects?.[item],
        };
      })
      .sort((a, b) => (a.name > b.name ? 1 : -1));

    const table = (
      <Table
        className="custom-table"
        size="small"
        columns={[
          { dataIndex: 'name', title: '参与方', width: 150 },
          {
            dataIndex: 'algorithmProjectUuid',
            title: '算法',
            render: (val) => (
              <AlgorithmProjectSelect
                algorithmType={[detail?.algorithm_type as EnumAlgorithmProjectType]}
                value={val}
                supportEdit={false}
              />
            ),
          },
        ]}
        scroll={{
          y: 300,
        }}
        border={false}
        borderCell={false}
        pagination={false}
        data={textList}
      />
    );
    const propsList = [
      {
        value: detail?.role
          ? detail.role === ModelJobRole.COORDINATOR
            ? '我方'
            : participantList.find((item) => item.id === detail.coordinator_id)?.name ||
              CONSTANTS.EMPTY_PLACEHOLDER
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: '发起方',
      },
      {
        label: '授权状态',
        value: (
          <ProgressWithText
            className={styles.model_progress_container}
            statusText={name}
            status={status}
            percent={percent}
            toolTipContent={
              detail?.auth_frontend_status &&
              [ModelGroupStatus.PART_AUTH_PENDING, ModelGroupStatus.SELF_AUTH_PENDING].includes(
                detail?.auth_frontend_status,
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
        ),
      },
      {
        value: detail?.creator_username ?? CONSTANTS.EMPTY_PLACEHOLDER,
        label: '创建者',
      },
      {
        value:
          datasetDetail?.dataset_kind === DatasetKindBackEndType.PROCESSED ? (
            <Space>
              <Link
                to={`/datasets/${DatasetKindBackEndType.PROCESSED.toLowerCase()}/detail/${
                  detail?.dataset_id
                }/dataset_job_detail`}
              >
                {datasetDetail?.name}
              </Link>
              {datasetDetail?.dataset_type === DatasetType__archived.STREAMING &&
                datasetJob?.time_range && (
                  <Tag color={datasetJob?.time_range?.hours === 1 ? 'arcoblue' : 'purple'}>
                    {datasetJob?.time_range?.hours === 1 ? '小时级' : '天级'}
                  </Tag>
                )}
            </Space>
          ) : (
            CONSTANTS.EMPTY_PLACEHOLDER
          ),
        label: '数据集',
      },
      {
        value: (
          <Popover
            popupHoverStay={true}
            content={table}
            position="bl"
            className={styles.algorithm_popover_padding}
          >
            <button className="custom-text-button">{'查看'}</button>
          </Popover>
        ),
        label: '算法',
      },
      {
        value: detail?.updated_at
          ? formatTimestamp(detail.updated_at)
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: '更新时间',
      },
      {
        value: detail?.created_at
          ? formatTimestamp(detail.created_at)
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: '创建时间',
      },
    ];
    isTreeAlgorithm(detail?.algorithm_type as EnumAlgorithmProjectType) && propsList.splice(4, 1);
    return propsList;
  }, [
    datasetDetail?.dataset_kind,
    datasetDetail?.dataset_type,
    datasetDetail?.name,
    detail,
    myPureDomainName,
    participantList,
    progressConfig,
    datasetJob?.time_range,
  ]);

  const columns = useMemo<ColumnProps<ModelJob>[]>(() => {
    return [
      {
        title: '名称',
        dataIndex: 'version',
        name: 'version',
        width: 120,
        render: (_, record) => {
          if (record.auto_update) {
            return (
              <Space>
                {`V${record.version}`}
                <Tag color="blue">定时</Tag>
              </Space>
            );
          }
          return `V${record.version}`;
        },
      },
      {
        title: '发起方',
        dataIndex: 'coordinator_id',
        name: 'coordinator_id',
        width: 100,
        render: (val, record) => {
          if (record.role === 'COORDINATOR') {
            return '我方';
          }
          return participantList.find((item) => item.id === val)?.name || '-';
        },
      },
      {
        title: '任务状态',
        dataIndex: 'status',
        name: 'status',
        width: 180,
        filteredValue: expression2Filter(urlState.filter).status,
        filters: statusFilters.filters,
        render: (_, record) => {
          return (
            <StateIndicator
              {...getModelJobStatus(record.status ?? ModelJobStatus.UNKNOWN, {
                isHideAllActionList: true,
              })}
            />
          );
        },
      },
      {
        title: '运行时长',
        dataIndex: 'running_time',
        name: 'running_time',
        width: 150,
        render: (_, record) => {
          let isRunning = false;
          let isStopped = true;
          let runningTime = 0;

          const { state } = record;
          const { RUNNING, STOPPED, COMPLETED, FAILED } = WorkflowState;
          isRunning = state === RUNNING;
          isStopped = [STOPPED, COMPLETED, FAILED].includes(state);

          if (isRunning || isStopped) {
            const { stopped_at, started_at } = record;
            runningTime = isStopped ? stopped_at! - started_at! : dayjs().unix() - started_at!;
          }
          return <CountTime time={runningTime} isStatic={!isRunning} />;
        },
      },
      {
        title: '开始时间',
        dataIndex: 'started_at',
        name: 'started_at',
        width: 150,
        sorter(a: ModelJob, b: ModelJob) {
          return (a?.started_at ?? 0) - (b?.started_at ?? 0);
        },
        render: (date: number) => (date ? formatTimestamp(date) : CONSTANTS.EMPTY_PLACEHOLDER),
      },
      {
        title: '结束时间',
        dataIndex: 'stopped_at',
        name: 'stopped_at',
        width: 150,
        sorter(a: ModelJob, b: ModelJob) {
          return (a?.stopped_at ?? 0) - (b?.stopped_at ?? 0);
        },
        render: (date: number) => (date ? formatTimestamp(date) : CONSTANTS.EMPTY_PLACEHOLDER),
      },
      {
        title: '操作',
        dataIndex: 'operation',
        name: 'operation',
        fixed: 'right',
        width: 120,
        render: (_: any, record) => (
          <>
            <span>
              <ModelJobDetailDrawer.Button
                id={record.id}
                text={'详情'}
                btnDisabled={record.status === ModelJobStatus.PENDING}
                datasetBatchType={datasetJob?.time_range?.hours === 1 ? 'hour' : 'day'}
              />
            </span>
            <button
              className="custom-text-button"
              style={{ marginLeft: 15 }}
              disabled={record.status !== ModelJobStatus.RUNNING}
              onClick={() => {
                stopModelJob(projectId!, record.id)
                  .then(() => {
                    Message.success('终止成功');
                    modelJobListQuery.refetch();
                  })
                  .catch((error) => Message.error(error.message));
              }}
            >
              终止
            </button>
          </>
        ),
      },
    ];
  }, [
    modelJobListQuery,
    participantList,
    projectId,
    urlState.filter,
    datasetJob?.time_range?.hours,
  ]);

  return (
    <SharedPageLayout
      title={
        <BackButton onClick={() => history.push(routes.ModelTrainList)}>{'模型训练'}</BackButton>
      }
      cardPadding={0}
    >
      <Spin loading={detailQuery.isFetching}>
        <div className={styles.detail_container}>
          <Row>
            <Col span={12}>
              <Space size="medium">
                <Avatar />
                <div>
                  <h3>{detail?.name ?? '....'}</h3>
                  <Space className={styles.detail_comment_space}>
                    {detail?.algorithm_type && (
                      <AlgorithmType
                        type={detail.algorithm_type as EnumAlgorithmProjectType}
                        tagProps={{
                          size: 'small',
                        }}
                      />
                    )}
                    <Tag size="small" style={{ fontWeight: 'normal' }}>
                      ID: {detail?.id}
                    </Tag>
                    <Tooltip content={detail?.comment}>
                      <div className={styles.detail_comment}>
                        {detail?.comment ?? CONSTANTS.EMPTY_PLACEHOLDER}
                      </div>
                    </Tooltip>
                  </Space>
                </div>
              </Space>
            </Col>
            <Col className={styles.detail_header_col} span={12}>
              <Space>
                {detail?.role === 'PARTICIPANT' && (
                  <Space>
                    <span>
                      {detail.authorized ? (
                        <>
                          <IconCheckCircleFill style={{ color: 'rgb(var(--success-6))' }} />
                          我方已授权
                        </>
                      ) : (
                        <>
                          <IconExclamationCircleFill style={{ color: 'rgb(var(--primary-6))' }} />
                          待我方授权
                        </>
                      )}
                    </span>
                    <button
                      className="custom-text-button"
                      onClick={() => {
                        Modal.confirm({
                          title: detail.authorized ? '确认撤销授权？' : '确认授权？',
                          content: detail.authorized
                            ? '撤销授权后，发起方不可运行模型训练，正在运行的任务不受影响'
                            : '授权后，发起方可以运行模型训练',
                          okText: '确认',
                          onOk: () => {
                            authorizeMutate.mutate({
                              id: detail.id,
                              authorized: !detail.authorized,
                            });
                          },
                        });
                      }}
                    >
                      {detail.authorized ? '撤销授权' : '授权'}
                    </button>
                  </Space>
                )}
                {/* TODO: 中心化后支持每个参与方发起模型训练任务 */}
                <Tooltip
                  content={
                    detail?.role === 'COORDINATOR' || !isOldModelGroup
                      ? undefined
                      : '旧版模型训练作业非发起方暂不支持发起模型训练任务'
                  }
                >
                  <Button
                    type="primary"
                    onClick={() => {
                      model_job_global_config_enabled && !isOldModelGroup
                        ? onStartModelTrainJobClick('once')
                        : onStartNewModelJobButtonClick();
                    }}
                    disabled={!detail?.name || (detail?.role !== 'COORDINATOR' && isOldModelGroup)}
                  >
                    发起新任务
                  </Button>
                </Tooltip>
                {model_job_global_config_enabled &&
                  !isOldModelGroup &&
                  datasetDetail?.dataset_type === DatasetType__archived.STREAMING &&
                  isVerticalNNAlgorithm(detail?.algorithm_type as EnumAlgorithmProjectType) && (
                    <Button
                      type="primary"
                      loading={autoBtnLoading}
                      onClick={async () => {
                        if (detail?.auto_update_status === AutoModelJobStatus.ACTIVE) {
                          setAutoBtnLoading(true);
                          Modal.stop({
                            title: '确定停止定时续训任务',
                            content: '请谨慎操作',
                            okText: '停止',
                            onOk: async () => {
                              try {
                                await stopAutoUpdateModelJob(projectId!, detail?.id!);
                                Message.success('停止定时续训任务成功');
                                detailQuery.refetch();
                              } catch (err: any) {
                                Message.error(err.message);
                              }
                              setAutoBtnLoading(false);
                            },
                            onCancel: () => {
                              setAutoBtnLoading(false);
                            },
                          });
                        } else {
                          onStartModelTrainJobClick('repeat');
                        }
                      }}
                      disabled={!detail?.name}
                    >
                      {
                        AUTO_STATUS_TEXT_MAPPER?.[
                          detail?.auto_update_status || AutoModelJobStatus.INITIAL
                        ]
                      }
                    </Button>
                  )}

                {isOldModelGroup && (
                  <Button onClick={onEditButtonClick} disabled={!detail?.name}>
                    编辑
                  </Button>
                )}
                <MoreActions
                  actionList={[
                    {
                      label: '删除',
                      danger: true,
                      onClick: onDeleteButtonClick,
                      disabled: !detail?.name,
                    },
                  ]}
                />
              </Space>
            </Col>
          </Row>
          <PropertyList
            cols={4}
            properties={isOldModelGroup ? displayedProps : displayedProps_new}
            align="center"
          />
        </div>
        <div className={styles.detail_content}>
          <div className={styles.table_header}>
            <Space>
              <LabelStrong>训练任务</LabelStrong>
              <Tag className={styles.round_tag}>{detail?.model_jobs?.length ?? 0}</Tag>
            </Space>
            {detail?.algorithm_type && (
              <TrainJobCompareModal.Button
                algorithmType={detail?.algorithm_type}
                list={(detail?.model_jobs ?? []).slice(0, 10) /** NOTE: 只取前十条训练任务来对比 */}
              />
            )}
          </div>
          <Table
            className="custom-table custom-table-left-side-filter"
            loading={modelJobListQuery.isFetching}
            data={modelJobList ?? []}
            rowKey="id"
            columns={columns}
            pagination={{
              ...paginationProps,
              total: modelJobListQuery.data?.page_meta?.total_items ?? modelJobList?.length,
            }}
            onChange={(_, __, filters, extra) => {
              if (extra.action === 'filter') {
                setUrlState((preState) => ({
                  ...preState,
                  page: 1,
                  filter: filterExpressionGenerator(
                    {
                      status: filters.status,
                    },
                    FILTER_MODEL_JOB_OPERATOR_MAPPER,
                  ),
                }));
              }
            }}
          />
        </div>
      </Spin>
    </SharedPageLayout>
  );

  async function onStartNewModelJobButtonClick() {
    let isPeerAuthorized = false;

    try {
      const resp = await fetchPeerModelJobGroupDetail(projectId!, params.id!, participantId!);
      isPeerAuthorized = resp?.data?.authorized ?? false;
    } catch (error) {
      Message.error(error.message);
    }

    if (!isPeerAuthorized) {
      Message.info('合作伙伴未授权，不能发起新任务');
      return;
    }

    launchModelJobGroup(projectId!, params.id)
      .then(() => {
        Message.success('发起成功');
        setUrlState({ page: 1, filter: undefined });
        modelJobListQuery.refetch();
      })
      .catch((error) => Message.error(error.message));
  }
  function onEditButtonClick() {
    history.push(
      generatePath(routes.ModelTrainCreate, {
        role: detail!.role === ModelJobRole.COORDINATOR ? 'sender' : 'receiver',
        action: 'edit',
        id: params.id,
      }),
    );
  }
  async function onStartModelTrainJobClick(type: string) {
    if (detail?.auth_frontend_status !== ModelGroupStatus.ALL_AUTHORIZED) {
      Message.info('所有合作伙伴授权通过后才可以发起模型训练任务');
      return false;
    }
    if (detail?.auto_update_status === AutoModelJobStatus.STOPPED && type === 'repeat') {
      if (!projectId || !detail?.id) {
        Message.info('请选择工作区！');
        return;
      }
      try {
        await fetchAutoUpdateModelJobDetail(projectId, detail?.id);
      } catch (err: any) {
        if (err.message.indexOf('is running') !== -1) {
          Message.info('有定时任务正在运行，请停止后重试！');
          return;
        }
      }
    }
    history.push(
      generatePath(routes.ModelTrainJobCreate, {
        type: type,
        id: params.id,
        step: 'coordinator',
      }),
    );
  }
  function onDeleteButtonClick() {
    Modal.delete({
      title: `确认要删除「${detail?.name}」？`,
      content: '删除后，该模型训练下的所有信息无法复原，请谨慎操作',
      onOk() {
        deleteModelJobGroup(projectId!, params.id)
          .then(() => {
            Message.success('删除成功');
            history.push(routes.ModelTrainList);
          })
          .catch((error) => Message.error(error.message));
      },
    });
  }
};
export default Detail;
