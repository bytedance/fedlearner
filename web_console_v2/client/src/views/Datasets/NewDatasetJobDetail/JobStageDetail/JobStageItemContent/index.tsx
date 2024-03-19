import React, { useMemo, FC, ReactElement } from 'react';
import { useQuery } from 'react-query';
import { useGetCurrentProjectId } from 'hooks';
import { fetchDatasetJobStageById, fetchDataBatchById } from 'services/dataset';
import { useParams } from 'react-router';
import { Message, Spin, Tooltip } from '@arco-design/web-react';
import PropertyList from 'components/PropertyList';
import WorkFlowPods from '../WorkFlowPods';
import JobParamsPanel from '../JobParamsPanel';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import { DatasetJobState, DatasetKindLabel } from 'typings/dataset';
import { getIntersectionRate } from 'shared/dataset';
import { formatTimeCount, formatTimestamp } from 'shared/date';
import { Link } from 'react-router-dom';
import dayjs from 'dayjs';
import CountTime from 'components/CountTime';
import { DatasetDetailSubTabs } from 'views/Datasets/DatasetDetail';
import ClickToCopy from 'components/ClickToCopy';
import { CONSTANTS } from 'shared/constants';
import styled from './index.module.less';

type Props = {
  jobStageId: ID;
  batchId: ID;
  isProcessed: boolean;
  isJoin: boolean;
  isExport: boolean;
  importDatasetId: ID | null;
};
const JobStageItemContent: FC<Props> = function (props: Props) {
  const { dataset_id, job_id } = useParams<{ dataset_id: string; job_id: string }>();
  const { jobStageId, batchId, isProcessed, isJoin, isExport, importDatasetId } = props;
  const projectId = useGetCurrentProjectId();
  const { isFetching, data } = useQuery(
    ['fetchDatasetJobStageById', projectId, job_id, jobStageId],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return;
      }
      return fetchDatasetJobStageById(projectId, job_id, jobStageId);
    },
    {
      retry: 2,
      enabled: Boolean(job_id) && Boolean(jobStageId),
    },
  );
  const { isFetching: isBatchFetch, data: batchData } = useQuery(
    ['fetchDataBatchById', dataset_id, batchId],
    () => {
      return fetchDataBatchById(dataset_id, batchId);
    },
    {
      retry: 2,
      enabled: Boolean(dataset_id) && Boolean(batchId),
    },
  );
  const {
    state,
    started_at = 0,
    finished_at = 0,
    input_data_batch_num_example = 0,
    output_data_batch_num_example = 0,
    workflow_id,
    global_configs,
  } = data?.data || {};
  const { name, path } = batchData?.data || {};
  const isRunning = state
    ? [DatasetJobState.PENDING, DatasetJobState.RUNNING].includes(state)
    : false;
  const basicInfo = useMemo(() => {
    function TimeRender(prop: { time: DateTime }) {
      const { time } = prop;
      return <span>{time <= 0 ? '-' : formatTimestamp(time)}</span>;
    }
    function RunningTimeRender(prop: { start: DateTime; finish: DateTime; isRunning: boolean }) {
      const { start, finish, isRunning } = prop;
      if (isRunning) {
        return start <= 0 ? (
          <span>待运行</span>
        ) : (
          <CountTime time={dayjs().unix() - start} isStatic={false} />
        );
      }
      return <span>{finish - start <= 0 ? '-' : formatTimeCount(finish - start)}</span>;
    }
    const basicInfoOptions: Array<{
      label: string;
      value: ReactElement | string | number;
    }> = [
      {
        label: '任务状态',
        value: renderDatasetJobState(state),
      },
      {
        label: '开始时间',
        value: <TimeRender time={started_at} />,
      },
      {
        label: '结束时间',
        value: <TimeRender time={finished_at} />,
      },
      {
        label: '运行时长',
        value: <RunningTimeRender start={started_at} finish={finished_at} isRunning={isRunning} />,
      },
    ];
    if (isExport) {
      basicInfoOptions.push(
        {
          label: '导出批次',
          value: (
            <Link
              to={`/datasets/${
                isProcessed ? DatasetKindLabel.PROCESSED : DatasetKindLabel.RAW
              }/detail/${importDatasetId}/${DatasetDetailSubTabs.Databatch}`}
            >
              {name}
            </Link>
          ),
        },
        {
          label: '导出路径',
          value: (
            <ClickToCopy text={path || ''}>
              <Tooltip content={path}>
                <div className={styled.export_path_text}>{path || CONSTANTS.EMPTY_PLACEHOLDER}</div>
              </Tooltip>
            </ClickToCopy>
          ),
        },
      );
    } else {
      basicInfoOptions.push(
        {
          label: '处理批次',
          value: (
            <Link
              to={`/datasets/${
                isProcessed ? DatasetKindLabel.PROCESSED : DatasetKindLabel.RAW
              }/detail/${dataset_id}/${DatasetDetailSubTabs.Databatch}`}
            >
              {name}
            </Link>
          ),
        },
        {
          label: '输入样本量',
          value: input_data_batch_num_example,
        },
        {
          label: '输出样本量',
          value: output_data_batch_num_example,
        },
      );
    }
    if (isJoin) {
      basicInfoOptions.push({
        label: '求交率',
        value: getIntersectionRate({
          input: input_data_batch_num_example,
          output: output_data_batch_num_example,
        }),
      });
    }
    return basicInfoOptions;
  }, [
    state,
    started_at,
    finished_at,
    input_data_batch_num_example,
    output_data_batch_num_example,
    isRunning,
    name,
    path,
    dataset_id,
    isProcessed,
    isJoin,
    isExport,
    importDatasetId,
  ]);
  return (
    <Spin loading={isFetching || isBatchFetch}>
      <div className={styled.job_stage_item_wrapper}>
        <h3 className={styled.title}>基本信息</h3>
        <PropertyList properties={basicInfo} cols={4} />
        {global_configs && !isExport && (
          <JobParamsPanel globalConfigs={global_configs.global_configs} />
        )}
        <WorkFlowPods workFlowId={workflow_id} />
      </div>
    </Spin>
  );

  function renderDatasetJobState(state: DatasetJobState | undefined) {
    let text: string;
    let type: StateTypes;
    switch (state) {
      case DatasetJobState.SUCCEEDED:
        text = '成功';
        type = 'success';
        break;
      case DatasetJobState.PENDING:
      case DatasetJobState.RUNNING:
        text = '运行中';
        type = 'processing';
        break;
      case DatasetJobState.FAILED:
        text = '失败';
        type = 'error';
        break;
      case DatasetJobState.STOPPED:
        text = '已停止';
        type = 'error';
        break;
      default:
        text = '未知';
        type = 'default';
    }
    return <StateIndicator text={text} type={type} />;
  }
};

export default JobStageItemContent;
