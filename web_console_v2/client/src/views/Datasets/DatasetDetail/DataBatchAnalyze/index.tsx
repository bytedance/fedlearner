import React, { FC, useState, useMemo, useCallback } from 'react';
import { useQuery } from 'react-query';
import {
  fetchDataBatchs,
  fetchDataBatchPreviewData,
  fetchDatasetJobStageById,
} from 'services/dataset';
import { useParams, useHistory } from 'react-router';
import { Left } from 'components/IconPark';
import { TIME_INTERVAL } from 'shared/constants';
import MoreActions from 'components/MoreActions';
import StructDataPreviewTable from 'components/DataPreview/StructDataTable';
import { DataBatchV2, DatasetStateFront } from 'typings/dataset';
import { Progress, Button, Spin, Message } from '@arco-design/web-react';
import emptyIcon from 'assets/images/empty.png';
import { useToggle } from 'react-use';
import DataBatchAnalyzeModal from './DataBatchAnalyzeModal';
import { formatTimestamp } from 'shared/date';
import { useGetCurrentProjectId } from 'hooks';
import {
  isDatasetJobStagePending,
  isDatasetJobStageFailed,
  isDatasetJobStageSuccess,
} from '../../shared';
import { JobDetailSubTabs } from 'views/Datasets/NewDatasetJobDetail';
import FeatureDrawer from './FeatureDrawer';
import { useFeatureDrawerClickOutside } from 'components/DataPreview/StructDataTable/hooks';

import styled from './index.module.less';

type TProps = {
  datasetJobId: ID;
  isOldData: boolean;
  onAnalyzeBatch: () => void;
};
const DataBatchAnalyze: FC<TProps> = function (props: TProps) {
  const projectId = useGetCurrentProjectId();
  const [collapsed, setCollapsed] = useState(true);
  const [total, setTotal] = useState(0);
  const [activeBatch, setActiveBatch] = useState<DataBatchV2>();
  const [visible, toggleVisible] = useToggle(false);
  const [activeKey, setActiveFeatKey] = useState<string | undefined>();
  const [drawerVisible, toggleDrawerVisible] = useToggle(false);
  const history = useHistory();
  const { id } = useParams<{
    id: string;
  }>();

  // generator listQuery
  const listQuery = useQuery(
    ['fetchDataBatchs', id],
    () => {
      return fetchDataBatchs(id!);
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST,
      onSuccess: (res) => {
        const { page_meta, data } = res || {};
        setTotal((pre) => page_meta?.total_items || pre);
        if (!activeBatch) {
          setActiveBatch(data[0]);
        } else {
          const newActiveBatch = data.find((item) => item.id === activeBatch.id);
          setActiveBatch(newActiveBatch || data[0]);
        }
      },
    },
  );

  const queryBatchState = useQuery(
    [
      'fetchDatasetJobStageById',
      projectId,
      props.datasetJobId,
      activeBatch?.latest_analyzer_dataset_job_stage_id,
    ],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return;
      }
      return fetchDatasetJobStageById(
        projectId,
        props.datasetJobId,
        activeBatch?.latest_analyzer_dataset_job_stage_id!,
      );
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.EXPORT_STATE_CHECK,
      enabled:
        Boolean(props.datasetJobId) &&
        Boolean(activeBatch) &&
        Boolean(activeBatch?.latest_analyzer_dataset_job_stage_id),
    },
  );

  const batchAnalyzeState = queryBatchState.data?.data;

  // ======= Preivew data query ============
  const previewDataQuery = useQuery(
    ['fetchDataBatchPreviewData', id, activeBatch?.id],
    () => fetchDataBatchPreviewData(id, activeBatch!?.id),
    {
      refetchOnWindowFocus: false,
      retry: 2,
      enabled:
        Boolean(id) && Boolean(activeBatch) && Boolean(isDatasetJobStageSuccess(batchAnalyzeState)),
    },
  );
  const list = useMemo(() => {
    return listQuery.data?.data || [];
  }, [listQuery.data]);

  const onDrawerClose = useCallback(() => {
    setActiveFeatKey(undefined);
  }, [setActiveFeatKey]);

  // When click outside struct data atable | feature drawer, close the drawer
  useFeatureDrawerClickOutside({ setActiveFeatKey, toggleDrawerVisible });
  return (
    <div className={styled.data_batch_analyze}>
      <div
        className={styled.data_batch_list_wrapper}
        style={{
          width: collapsed ? '212px' : '0px',
        }}
      >
        {collapsed && (
          <div className={styled.data_batch_list}>
            <div className={styled.data_batch_list_header}>批次列表</div>
            {list.map((item, index) => (
              <div
                key={index}
                className={`${styled.data_batch_list_item} ${
                  item.id === activeBatch?.id ? styled.active : ''
                }`}
                onClick={() => {
                  handleChangeBatch(item);
                }}
              >
                <div className={styled.data_batch_list_item_title}>批次 {item.name}</div>
                <div className={styled.data_batch_list_item_time}>
                  {formatTimestamp(item.updated_at, 'YYYY-MM-DD HH:mm')}
                </div>
                <MoreActions
                  className={styled.data_batch_list_item_action}
                  actionList={[
                    {
                      label: '查看任务详情',
                      onClick: () => onDetailClick(item),
                    },
                  ]}
                />
              </div>
            ))}
            <div className={styled.data_batch_list_count}>{total}个记录</div>
          </div>
        )}
        <div
          onClick={() => setCollapsed(!collapsed)}
          className={collapsed ? styled.collapse : styled.is_reverse}
        >
          <Left />
        </div>
      </div>
      <div className={styled.data_batch_content}>
        {!activeBatch ? renderNoBatch() : renderBatchDetail()}
      </div>
      {activeBatch && (
        <DataBatchAnalyzeModal
          visible={visible}
          toggleVisible={toggleVisible}
          dataBatch={activeBatch}
          onSuccess={handleAnalyzeSuccess}
        />
      )}
      {activeBatch && (
        <FeatureDrawer
          id={id}
          batchId={activeBatch.id}
          toggleDrawerVisible={toggleDrawerVisible}
          visible={drawerVisible}
          activeKey={activeKey}
          onClose={onDrawerClose}
        />
      )}
    </div>
  );

  function renderNoBatch() {
    return (
      <div className={styled.data_batch_no_success}>
        <img alt="" src={emptyIcon} className={styled.empty} />
        <span className={styled.no_batch_preview}>无数据批次</span>
      </div>
    );
  }

  function renderBatchDetail() {
    return (
      <>
        {activeBatch?.latest_analyzer_dataset_job_stage_id === 0 ? (
          renderNoDoBatch()
        ) : (
          <>
            {isDatasetJobStagePending(batchAnalyzeState) && renderProcessBatch()}
            {isDatasetJobStageFailed(batchAnalyzeState) && renderFailedBatch()}
            {isDatasetJobStageSuccess(batchAnalyzeState) && renderSuccessBatch()}
          </>
        )}
      </>
    );
  }

  function renderNoDoBatch() {
    const batchActionMap = {
      [DatasetStateFront.SUCCEEDED]: () => (
        <Button type="primary" style={{ width: '136px' }} onClick={openAnalyzeModel}>
          发起探查
        </Button>
      ),
      [DatasetStateFront.PENDING]: () => (
        <span className={styled.no_batch_preview}>当前数据批次待处理， 请稍后探查</span>
      ),
      [DatasetStateFront.PROCESSING]: () => (
        <span className={styled.no_batch_preview}>当前数据批次正在处理， 请稍后探查</span>
      ),
      [DatasetStateFront.FAILED]: () => (
        <span className={styled.no_batch_preview}>当前数据批次处理失败， 无法探查</span>
      ),
      [DatasetStateFront.DELETING]: () => (
        <span className={styled.no_batch_preview}>当前数据批次正在删除， 无法探查</span>
      ),
    };
    return (
      <div className={styled.data_batch_no_success}>
        <img alt="" src={emptyIcon} className={styled.empty} />
        <span className={styled.no_batch_preview}>无探查数据</span>
        {activeBatch?.state && batchActionMap[activeBatch.state]()}
      </div>
    );
  }

  function renderProcessBatch() {
    return (
      <div className={styled.data_batch_no_success}>
        <Spin size={50} className={styled.data_batch_loading} />
        <span className={styled.no_batch_preview}>数据探查中，可能会耗时较长…</span>
      </div>
    );
  }

  function renderFailedBatch() {
    return (
      <div className={styled.data_batch_no_success}>
        <Progress type="circle" size="large" percent={50} status="error" />
        <span className={styled.no_batch_preview}>数据探查失败</span>
        <Button type="text" style={{ width: 136 }} onClick={openAnalyzeModel}>
          点击重试
        </Button>
      </div>
    );
  }
  function renderSuccessBatch() {
    return (
      <StructDataPreviewTable
        data={previewDataQuery.data?.data}
        loading={previewDataQuery.isFetching}
        isError={previewDataQuery.isError}
        onActiveFeatChange={onActiveFeatChange}
        {...props}
      />
    );
  }
  function handleChangeBatch(batch: DataBatchV2) {
    setActiveBatch(batch);
  }

  function openAnalyzeModel() {
    toggleVisible(true);
  }

  function handleAnalyzeSuccess() {
    // hook 方法， 现在analyze_job_id 存在了 dataset 实体上， 所以需要刷新下dataset数据
    props.onAnalyzeBatch();
    listQuery.refetch();
  }

  function onActiveFeatChange(featKey: string) {
    setActiveFeatKey(featKey);
    toggleDrawerVisible(true);
  }

  function onDetailClick(dataBatch: DataBatchV2) {
    if (dataBatch.latest_analyzer_dataset_job_stage_id === 0) {
      Message.warning('发起数据探查后才可查看详情');
    } else {
      if (props.isOldData) {
        history.push(`/datasets/job_detail/${props.datasetJobId}`);
      } else {
        history.push(
          `/datasets/${id}/new/job_detail/${queryBatchState.data?.data.dataset_job_id}/${JobDetailSubTabs.TaskList}`,
        );
      }
    }
  }

  // function onDeleteClick() {}
};

export default DataBatchAnalyze;
