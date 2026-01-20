import React, {
  useState,
  useMemo,
  ForwardRefRenderFunction,
  forwardRef,
  useImperativeHandle,
} from 'react';
import { useQuery } from 'react-query';
import { Left } from 'components/IconPark';
import { DatasetJobStage, DatasetJobState } from 'typings/dataset';
import { useGetCurrentProjectId } from 'hooks';
import { fetchDatasetJobStageList } from 'services/dataset';
import { useParams, useLocation } from 'react-router';
import { Message } from '@arco-design/web-react';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import JobStageItemContent from './JobStageItemContent';
import qs from 'qs';
import styled from './index.module.less';

type ExposedRef = {
  refetch: () => void;
};

type Props = {
  isProcessed: boolean;
  isJoin: boolean; // 表示是否是求交任务
  isExport: boolean; // 表示是否是导出任务
  importDatasetId: ID | null;
};
const JobStageDetail: ForwardRefRenderFunction<ExposedRef, Props> = function (
  props: Props,
  parentRef,
) {
  const { job_id } = useParams<{ job_id: string }>();
  const projectId = useGetCurrentProjectId();
  const [collapsed, setCollapsed] = useState(true);
  const [total, setTotal] = useState(0);
  const [activeJobStage, setActiveJobStage] = useState<DatasetJobStage>();
  const location = useLocation();
  const query = location.search || '';
  const queryObject = qs.parse(query.slice(1)) || {};
  const listQuery = useQuery(
    ['fetchDatasetJobStageList', projectId, job_id],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return;
      }
      return fetchDatasetJobStageList(projectId!, job_id);
    },
    {
      retry: 2,
      onSuccess: (res) => {
        if (!res) return;
        const { page_meta, data } = res || {};
        setTotal((pre) => page_meta?.total_items || pre);
        if (queryObject.stageId) {
          const activeJobStage = data.find((item) => `${item.id}` === queryObject.stageId);
          setActiveJobStage(activeJobStage || data[0]);
        } else {
          setActiveJobStage(data[0]);
        }
      },
    },
  );

  const list = useMemo(() => {
    return listQuery.data?.data || [];
  }, [listQuery.data]);

  useImperativeHandle(parentRef, () => {
    return {
      refetch: listQuery.refetch,
    };
  });

  return (
    <div className={styled.dataset_job_stage_wrapper}>
      <div
        className={styled.job_stage_list_wrapper}
        style={{
          width: collapsed ? '212px' : '0px',
        }}
      >
        {collapsed && (
          <div className={styled.job_stage_list}>
            <div className={styled.job_stage_list_header}>任务</div>
            {list.map((item, index) => (
              <div
                key={index}
                className={`${styled.job_stage_list_item} ${
                  item.id === activeJobStage?.id ? styled.active : ''
                }`}
                onClick={() => {
                  handleChangeJobStage(item);
                }}
              >
                <div className={styled.job_stage_list_item_title}>{item.name}</div>
                {renderDatasetJobState(item)}
              </div>
            ))}
            <div className={styled.job_stage_list_count}>{total}个记录</div>
          </div>
        )}
        <div
          onClick={() => setCollapsed(!collapsed)}
          className={collapsed ? styled.collapse : styled.is_reverse}
        >
          <Left />
        </div>
      </div>
      <div className={styled.job_stage_content}>
        {activeJobStage && (
          <JobStageItemContent
            {...props}
            jobStageId={activeJobStage.id}
            batchId={activeJobStage.output_data_batch_id}
          />
        )}
      </div>
    </div>
  );
  function renderDatasetJobState(stage: DatasetJobStage) {
    let text: string;
    let type: StateTypes;
    switch (stage.state) {
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
    }
    return <StateIndicator text={text} type={type} />;
  }
  function handleChangeJobStage(stage: DatasetJobStage) {
    setActiveJobStage(stage);
  }
};

export default forwardRef(JobStageDetail);
