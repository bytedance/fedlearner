import { Button, Grid, Message, Space, Spin, Tabs, Tooltip, Tag } from '@arco-design/web-react';
import BackButton from 'components/BackButton';
import PictureDataPreviewTable from 'components/DataPreview/PictureDataTable';
import PropertyList from 'components/PropertyList';
import SharedPageLayout from 'components/SharedPageLayout';
import GridRow from 'components/_base/GridRow';
import { isNil } from 'lodash-es';
import React, { FC, useEffect, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { Redirect, Route, useHistory, useParams } from 'react-router';
import { useToggle } from 'react-use';
import {
  deleteDataset,
  fetchDatasetDetail,
  fetchDatasetPreviewData,
  fetchDataBatchs,
  fetchDatasetJobDetail,
  fetchDatasetFlushAuthStatus,
  authorizeDataset,
  cancelAuthorizeDataset,
  stopDatasetStreaming,
} from 'services/dataset';
import {
  getImportStage,
  getTotalDataSize,
  isFrontendDeleting,
  isFrontendProcessing,
  isFrontendSucceeded,
} from 'shared/dataset';
import { formatTimestamp } from 'shared/date';
import { humanFileSize } from 'shared/file';
import {
  Dataset,
  DatasetDataType,
  DatasetKindLabel,
  DATASET_COPY_CHECKER,
  DatasetType__archived,
  DatasetProcessedAuthStatus,
  ParticipantInfo,
  DatasetProcessedMyAuthStatus,
  DatasetKindBackEndType,
  DatasetJobSchedulerState,
} from 'typings/dataset';
import { datasetPageTitles, isDataJoin, RawAuthStatusOptions, isHoursCronJoin } from '../shared';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import { CONSTANTS, TIME_INTERVAL } from 'shared/constants';
import CodeEditorDrawer from 'components/CodeEditorDrawer';
import TaskDetail, { NodeType } from '../TaskDetail';
import ProcessedDatasetTable from './ProcessedDatasetTable';
import DatasetJobStageList from './DatasetJobStageList';
import ClickToCopy from 'components/ClickToCopy';
import {
  IconCheckCircleFill,
  IconCloseCircleFill,
  IconQuestionCircle,
} from '@arco-design/web-react/icon';
import MoreActions from 'components/MoreActions';
import Modal from 'components/Modal';
import DatasetEditModal from '../DatasetList/DatasetEditModal';
import DatasetPublishAndRevokeModal from 'components/DatasetPublishAndRevokeModal';
import BlockchainStorageTable from 'components/BlockchainStorageTable';
import StatusProgress from 'components/StatusProgress';
import DataBatchTable from './DataBatchTable/index';
import DataBatchAnalyze from './DataBatchAnalyze/index';
import { useGetAppFlagValue, useGetCurrentProjectId } from 'hooks';
import { FlagKey } from 'typings/flag';
import ImportProgress from '../DatasetList/ImportProgress/index';
import { getIntersectionRate } from 'shared/dataset';
import { fetchSysInfo } from 'services/settings';
import { to } from 'shared/helpers';
import styled from './index.module.less';

const { Row } = Grid;

const { TabPane } = Tabs;

export enum DatasetDetailSubTabs {
  PreviewData = 'preview',
  Schema = 'schema',
  Image = 'image',
  RelativeDataset = 'relative_dataset',
  Databatch = 'data_batch',
  DatasetJobDetail = 'dataset_job_detail',
  BlockchainStorage = 'blockchain_storage',
}

const DatasetDetail: FC<any> = () => {
  const history = useHistory();
  const projectId = useGetCurrentProjectId();

  const { kind_label, id, subtab } = useParams<{
    kind_label: DatasetKindLabel;
    id: string;
    subtab: string;
  }>();
  const isProcessedDataset = kind_label === DatasetKindLabel.PROCESSED;
  const isRaw = kind_label === DatasetKindLabel.RAW;
  const [activeTab, setActiveTab] = useState(subtab || DatasetDetailSubTabs.PreviewData);
  const [isShowPublishModal, setIsShowPublishModal] = useState(false);
  const [selectDataset, setSelectDataset] = useState<Dataset>();
  const [editModalVisible, toggleEditModalVisible] = useToggle(false);
  const bcs_support_enabled = useGetAppFlagValue(FlagKey.BCS_SUPPORT_ENABLED);

  const sysInfoQuery = useQuery(['fetchSysInfo'], () => fetchSysInfo(), {
    retry: 2,
    refetchOnWindowFocus: false,
    enabled: Boolean(isProcessedDataset),
  });

  const myPureDomainName = useMemo<string>(() => {
    return sysInfoQuery.data?.data?.pure_domain_name ?? '';
  }, [sysInfoQuery.data]);

  // 授权兜底策略， 前端刷新下接口
  useQuery(['fetchDatasetFlushAuthStatus', id], () => fetchDatasetFlushAuthStatus(id), {
    refetchOnWindowFocus: false,
    enabled: Boolean(isProcessedDataset),
    onSuccess() {
      query.refetch();
    },
  });

  // ======= Dataset query ============
  const query = useQuery(['fetchDatasetDetail', id], () => fetchDatasetDetail(id), {
    refetchOnWindowFocus: false,
    refetchInterval: TIME_INTERVAL.CONNECTION_CHECK,
  });

  const datasetJobQuery = useQuery(
    ['fetchDatasetJobDetail', projectId, query.data?.data.parent_dataset_job_id],
    () => fetchDatasetJobDetail(projectId!, query.data?.data.parent_dataset_job_id!),
    {
      refetchOnWindowFocus: false,
      retry: 2,
      enabled: Boolean(projectId && query.data?.data.parent_dataset_job_id),
    },
  );
  // ======= Preivew data query ============
  const previewDataQuery = useQuery(
    ['fetchDatasetPreviewData', id],
    () => fetchDatasetPreviewData(id),
    {
      refetchOnWindowFocus: false,
      retry: 2,
      enabled:
        Boolean(id) && [DatasetDetailSubTabs.Image].includes(activeTab as DatasetDetailSubTabs),
    },
  );

  const batchListQuery = useQuery(
    ['fetchDataBatchs', id],
    () => {
      return fetchDataBatchs(id!);
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST,
    },
  );

  const isAnalyzeSuccess = useMemo(() => {
    const data = batchListQuery.data?.data || [];
    return data.some((item) => item.latest_analyzer_dataset_job_stage_id !== 0);
  }, [batchListQuery.data]);
  const stateInfo = useMemo<{
    text: string;
    type: StateTypes;
    noResultText: string;
  }>(() => {
    if (query.data?.data) {
      const { text, type } = getImportStage(query.data.data);
      let noResultText = '';
      if (type === 'processing') {
        noResultText = '数据处理中，请稍后';
      }
      return { text, type, noResultText };
    }

    return {
      text: '状态未知',
      type: 'default',
      noResultText: '抱歉，数据暂时无法显示',
    };
  }, [query]);

  useEffect(() => {
    setActiveTab(subtab || DatasetDetailSubTabs.PreviewData);
  }, [subtab]);

  const datasetJobGlobalConfigs = useMemo(() => {
    if (!datasetJobQuery.data?.data?.global_configs?.global_configs) {
      return {};
    }
    return datasetJobQuery.data?.data?.global_configs?.global_configs;
  }, [datasetJobQuery]);

  const dataset = query.data?.data;

  const {
    dataset_format,
    dataset_kind,
    updated_at,
    num_feature,
    num_example,
    path,
    is_published,
    import_type,
    dataset_type,
    analyzer_dataset_job_id,
    parent_dataset_job_id,
    auth_frontend_state,
    local_auth_status,
    participants_info = { participants_map: {} },
  } = dataset ?? {};

  const datasetJob = datasetJobQuery.data?.data;
  const {
    has_stages,
    input_data_batch_num_example = 0,
    output_data_batch_num_example = 0,
    kind,
    scheduler_state,
    scheduler_message,
  } = datasetJob ?? {};
  const isOldData = !Boolean(has_stages);
  const isJoin = isDataJoin(kind);
  const datasetRate = getIntersectionRate({
    input: input_data_batch_num_example,
    output: output_data_batch_num_example,
  });
  const isDatasetStructType = dataset_format === DatasetDataType.STRUCT;
  const isDatasetPictureType = dataset_format === DatasetDataType.PICTURE;
  const isDatasetNoneStructType = dataset_format === DatasetDataType.NONE_STRUCTURED;
  const isCopy = !import_type || import_type === DATASET_COPY_CHECKER.COPY;
  const isStreaming = dataset_type === DatasetType__archived.STREAMING;
  const isStreamRunable = scheduler_state === DatasetJobSchedulerState.RUNNABLE;
  const isStreamStopped = scheduler_state === DatasetJobSchedulerState.STOPPED;
  const isAuthorized = local_auth_status === DatasetProcessedMyAuthStatus.AUTHORIZED;
  const isInternalProcessed = dataset_kind === DatasetKindBackEndType.INTERNAL_PROCESSED;
  const isHideAuth = Boolean(Object.keys(participants_info.participants_map).length === 0);
  /** IF no subtab be set, defaults to preview */
  if (!subtab) {
    return (
      <Redirect to={`/datasets/${kind_label}/detail/${id}/${DatasetDetailSubTabs.PreviewData}`} />
    );
  }
  if (isInternalProcessed && subtab === DatasetDetailSubTabs.DatasetJobDetail) {
    return (
      <Redirect to={`/datasets/${kind_label}/detail/${id}/${DatasetDetailSubTabs.Databatch}`} />
    );
  }
  const isProcessing = dataset ? isFrontendProcessing(dataset) : false;
  const isDeleting = dataset ? isFrontendDeleting(dataset) : false;

  const displayedProps = [
    {
      value: isNil(dataset_format)
        ? CONSTANTS.EMPTY_PLACEHOLDER
        : isDatasetStructType
        ? '结构化数据'
        : isDatasetPictureType
        ? '图片'
        : '非结构化数据',
      label: '数据格式',
      proport: 0.5,
    },
    {
      value: isInternalProcessed ? '-' : dataset ? humanFileSize(getTotalDataSize(dataset)) : '0 B',
      label: '数据大小',
      proport: 0.5,
    },
    {
      value: !isCopy || isInternalProcessed ? '-' : num_feature?.toLocaleString('en') || '0',
      label: '总列数',
      proport: 0.5,
    },
    {
      value: !isCopy || isInternalProcessed ? '-' : num_example?.toLocaleString('en') || '0',
      label: '总行数',
      proport: 0.5,
    },
    isStreaming && {
      value: isStreamStopped ? (
        <StateIndicator type="error" text="已停止" tag={false} />
      ) : (
        <span className={styled.dataset_detail_cron}>
          {isHoursCronJoin(datasetJob) ? '每小时' : '每天'}
          <Tooltip content={scheduler_message}>
            <IconQuestionCircle className={styled.data_detail_icon_question_circle} />
          </Tooltip>
        </span>
      ),
      label: isRaw ? '导入周期' : '求交周期',
      proport: 0.5,
    },
    {
      value: (
        <ClickToCopy text={path || ''}>
          <Tooltip content={path}>
            <div className={styled.data_source_text}>{path || CONSTANTS.EMPTY_PLACEHOLDER}</div>
          </Tooltip>
        </ClickToCopy>
      ),
      label: '数据集路径',
      proport: 2,
    },
    {
      value: updated_at ? formatTimestamp(updated_at) : CONSTANTS.EMPTY_PLACEHOLDER,
      label: '最近更新',
      proport: 1,
    },
    dataset?.validation_jsonschema &&
      Object.keys(dataset.validation_jsonschema).length > 0 &&
      ({
        value: (
          <CodeEditorDrawer.Button
            title="校验规则"
            value={JSON.stringify(dataset?.validation_jsonschema, null, 2)}
          />
        ),
        label: '校验规则',
        proport: 0.5,
      } as any),
  ].filter(Boolean);

  return (
    <SharedPageLayout
      title={<BackButton onClick={backToList}>{datasetPageTitles[kind_label]}</BackButton>}
      cardPadding={0}
    >
      <div className={styled.dataset_detail_padding_box}>
        <Spin loading={query.isFetching || datasetJobQuery.isFetching}>
          <Row align="center" justify="space-between">
            <GridRow gap="12" style={{ maxWidth: '75%' }}>
              <div
                className={styled.dataset_detail_avatar}
                data-name={query.data?.data.name.slice(0, 2)}
              />
              <div>
                <div className={styled.dataset_name_container}>
                  <h3 className={styled.dataset_name}>{query.data?.data.name ?? '....'}</h3>
                  {query.data && <ImportProgress dataset={query.data.data} tag={false} />}
                </div>
                {(isStreaming || !isCopy || query.data?.data.comment) && (
                  <Space>
                    {isStreaming && <Tag color="blue">增量</Tag>}
                    {!isCopy && <Tag>{'非拷贝'}</Tag>}
                    {query.data?.data.comment && (
                      <small className={styled.comment}>{query.data?.data.comment}</small>
                    )}
                  </Space>
                )}
              </div>
            </GridRow>

            <Space>
              {!isProcessedDataset && (
                <Space>
                  {is_published ? (
                    <IconCheckCircleFill style={{ color: 'var(--successColor)' }} />
                  ) : (
                    <IconCloseCircleFill style={{ color: 'var(--warningColor)' }} />
                  )}
                  <span>{is_published ? '已发布至工作区' : '未发布至工作区'}</span>
                  <Button
                    type={is_published ? 'default' : 'primary'}
                    onClick={onPublishClick}
                    disabled={dataset ? !isFrontendSucceeded(dataset) : true}
                  >
                    {is_published ? '撤销发布' : '发布'}
                  </Button>
                </Space>
              )}
              {isProcessedDataset && isInternalProcessed && renderAuthStatus()}
              {isProcessedDataset && !isHideAuth && (
                <Button type={isAuthorized ? 'default' : 'primary'} onClick={onAuthClick}>
                  {isAuthorized ? '撤销授权' : '授权'}
                </Button>
              )}
              {isStreaming && isStreamRunable && (
                <Button type="default" onClick={onStopStreaming}>
                  {isProcessedDataset ? '终止定时求交' : '终止增量导入'}
                </Button>
              )}
              <MoreActions
                actionList={[
                  {
                    label: '编辑',
                    onClick: onEditClick,
                    disabled: !dataset || isProcessing || isDeleting,
                  },
                  {
                    label: '删除',
                    onClick: onDeleteClick,
                    danger: true,
                    disabled: !dataset || isProcessing || isDeleting,
                  },
                ]}
              />
            </Space>
          </Row>
        </Spin>
        <PropertyList
          properties={displayedProps}
          cols={displayedProps.length}
          minWidth={150}
          align="center"
          colProportions={displayedProps.map((item) => item.proport)}
        />
      </div>
      <Tabs activeTab={activeTab} onChange={onSubtabChange} className={styled.data_detail_tab}>
        {!isInternalProcessed && (
          <TabPane
            className={styled.data_detail_tab_pane}
            title="任务详情"
            key={DatasetDetailSubTabs.DatasetJobDetail}
          />
        )}
        {isDatasetPictureType && isAnalyzeSuccess && (
          <TabPane
            className={styled.data_detail_tab_pane}
            title="图片预览"
            key={DatasetDetailSubTabs.Image}
          />
        )}
        <TabPane
          className={styled.data_detail_tab_pane}
          title="数据批次"
          key={DatasetDetailSubTabs.Databatch}
        />
        {isCopy && !isDatasetNoneStructType && (
          <TabPane
            className={styled.data_detail_tab_pane}
            title="数据探查"
            key={DatasetDetailSubTabs.PreviewData}
          />
        )}
        <TabPane
          className={styled.data_detail_tab_pane}
          title={
            <span>
              下游数据集
              <Tooltip content="通过使用本数据集所产生的数据集">
                <IconQuestionCircle className={styled.data_detail_icon_question_circle} />
              </Tooltip>
            </span>
          }
          key={DatasetDetailSubTabs.RelativeDataset}
        />
        {isRaw && bcs_support_enabled && (
          <TabPane
            className={styled.data_detail_tab_pane}
            title="区块链存证"
            key={DatasetDetailSubTabs.BlockchainStorage}
          />
        )}
      </Tabs>
      <div
        className={`${styled.dataset_detail_padding_box} ${
          activeTab === DatasetDetailSubTabs.PreviewData ? styled.dataset_detail_box : ''
        } ${activeTab === DatasetDetailSubTabs.Databatch ? styled.dataset_detail_batch_box : ''}`}
      >
        <Route
          path={`/datasets/:kind_label/detail/:id/${DatasetDetailSubTabs.Databatch}`}
          exact
          render={() => {
            return (
              <DataBatchTable
                datasetJobId={parent_dataset_job_id!}
                isOldData={isOldData}
                isDataJoin={isJoin}
                isCopy={isCopy}
                datasetRate={datasetRate}
                kind={kind!}
                isInternalProcessed={isInternalProcessed}
                globalConfigs={datasetJobGlobalConfigs}
              />
            );
          }}
        />
        {isCopy && (
          <Route
            path={`/datasets/:kind_label/detail/:id/${DatasetDetailSubTabs.PreviewData}`}
            exact
            render={(props) => {
              return (
                <DataBatchAnalyze
                  {...props}
                  datasetJobId={analyzer_dataset_job_id!}
                  isOldData={isOldData}
                  onAnalyzeBatch={() => {
                    query.refetch();
                  }}
                />
              );
            }}
          />
        )}
        {isDatasetPictureType && isAnalyzeSuccess && (
          <Route
            path={`/datasets/:kind_label/detail/:id/${DatasetDetailSubTabs.Image}`}
            exact
            render={(props) => {
              return (
                <PictureDataPreviewTable
                  data={previewDataQuery.data?.data}
                  loading={previewDataQuery.isFetching}
                  isError={previewDataQuery.isError}
                  noResultText={stateInfo.noResultText}
                />
              );
            }}
          />
        )}

        <Route
          path={`/datasets/:kind_label/detail/:id/${DatasetDetailSubTabs.DatasetJobDetail}`}
          exact
          render={() => {
            return (
              <>
                <TaskDetail
                  middleJump={true}
                  datasetId={id}
                  datasetJobId={dataset?.parent_dataset_job_id}
                  isShowRatio={false}
                  isOldData={isOldData}
                  onNodeClick={(node) => {
                    if (node.type === NodeType.DATASET_PROCESSED) {
                      onSubtabChange(DatasetDetailSubTabs.PreviewData);
                    }
                  }}
                  // TODO: pass error message when state_frontend = DatasetStateFront.FAILED,
                  errorMessage=""
                  isProcessedDataset={isProcessedDataset}
                />
                {(parent_dataset_job_id || parent_dataset_job_id === 0) && (
                  <DatasetJobStageList datasetId={id} datasetJobId={parent_dataset_job_id!} />
                )}
              </>
            );
          }}
        />
        <Route
          path={`/datasets/:kind_label/detail/:id/${DatasetDetailSubTabs.RelativeDataset}`}
          exact
          render={() => {
            return <ProcessedDatasetTable datasetId={id} />;
          }}
        />
        <Route
          path={`/datasets/:kind_label/detail/:id/${DatasetDetailSubTabs.BlockchainStorage}`}
          exact
          render={() => {
            return <BlockchainStorageTable datasetId={id} />;
          }}
        />
      </div>
      {dataset && (
        <DatasetEditModal
          dataset={dataset}
          visible={editModalVisible}
          toggleVisible={toggleEditModalVisible}
          onSuccess={onEditSuccess}
        />
      )}

      <DatasetPublishAndRevokeModal
        onCancel={onPublishCancel}
        onSuccess={onPublishSuccess}
        dataset={selectDataset}
        visible={isShowPublishModal}
      />
    </SharedPageLayout>
  );

  function renderParticipantAuth(val: ParticipantInfo[]) {
    return (
      <>
        {val.map((participant, index) => (
          <div key={index}>
            {participant.name}{' '}
            {participant.auth_status === DatasetProcessedMyAuthStatus.AUTHORIZED
              ? '已授权'
              : '未授权'}
          </div>
        ))}
      </>
    );
  }

  function renderAuthStatus() {
    if (auth_frontend_state === DatasetProcessedAuthStatus.AUTH_PENDING) {
      const participants_info_map = Object.entries(participants_info.participants_map || {}).map(
        ([key, value]) => ({
          name: key === myPureDomainName ? '我方' : key,
          auth_status: value['auth_status'],
        }),
      );
      return (
        <StatusProgress
          className={styled.dataset_detal_auth_status}
          options={RawAuthStatusOptions}
          status={auth_frontend_state || DatasetProcessedAuthStatus.AUTH_PENDING}
          isTip={true}
          toolTipContent={renderParticipantAuth(participants_info_map)}
        />
      );
    }
    return (
      <StatusProgress
        className={styled.dataset_detal_auth_status}
        options={RawAuthStatusOptions}
        status={auth_frontend_state || DatasetProcessedAuthStatus.TICKET_PENDING}
      />
    );
  }

  function onPublishSuccess() {
    setIsShowPublishModal(false);
    query.refetch();
  }
  function onPublishCancel() {
    setIsShowPublishModal(false);
  }

  function backToList() {
    history.goBack();
  }

  function onPublishClick() {
    if (!dataset) {
      return;
    }
    setSelectDataset(dataset);
    setIsShowPublishModal(true);
  }
  async function onAuthClick() {
    try {
      if (isAuthorized) {
        await cancelAuthorizeDataset(id);
      } else {
        await authorizeDataset(id);
      }
      query.refetch();
    } catch (err: any) {
      Message.error(err.message);
    }
  }

  function onStopStreaming() {
    Modal.delete({
      title: `确定终止${isProcessedDataset ? '定时求交' : '增量导入'}`,
      content: '终止后将无法被重启，请谨慎操作',
      okText: '终止',
      onOk: async () => {
        if (!projectId) {
          Message.info('请选择工作区');
          return;
        }
        if (!parent_dataset_job_id) {
          return;
        }
        const [, err] = await to(stopDatasetStreaming(projectId, parent_dataset_job_id));
        if (err) {
          Message.error(err.message || '终止失败');
          return;
        }
        Message.success('终止成功');
        datasetJobQuery.refetch();
      },
    });
  }
  function onEditClick() {
    toggleEditModalVisible(true);
  }
  function onEditSuccess() {
    query.refetch();
  }
  function onDeleteClick() {
    Modal.delete({
      title: '确认删除数据集？',
      content: '删除操作无法恢复，请谨慎操作',
      onOk: async () => {
        if (!dataset) {
          return;
        }
        try {
          const resp = await deleteDataset(dataset.id);
          // If delete success, HTTP response status code is 204, resp is empty string
          const isDeleteSuccess = !resp;
          if (isDeleteSuccess) {
            Message.success('删除成功');
            history.replace(`/datasets/${kind_label}`);
          } else {
            const errorMessage = resp?.message ?? '删除失败';
            Message.error(errorMessage!);
          }
        } catch (error) {
          Message.error(error.message);
        }
      },
    });
  }

  function onSubtabChange(val: string) {
    setActiveTab(val as DatasetDetailSubTabs);
    history.replace(`/datasets/${kind_label}/detail/${id}/${val}`);
  }
};

export default DatasetDetail;
