import React, { FC, useMemo, useState } from 'react';
import SharedPageLayout from 'components/SharedPageLayout';
import TaskDetail, { NodeType } from '../TaskDetail';
import JobParamsPanel from './JobParamsPanel';
import { useParams } from 'react-router-dom';
import JobTitle from './JobTitle';
import { useQuery } from 'react-query';
import { fetchDatasetJobDetail } from 'services/dataset';
import { useGetCurrentProjectId } from 'hooks';
import { DatasetJob, DatasetJobState } from 'typings/dataset';
import { get } from 'lodash-es';
import JobBasicInfo from './JobBasicInfo';
import WorkFlowPods from './WorkFlowPods';
import { DatasetDetailSubTabs } from '../DatasetDetail';
import { useHistory } from 'react-router';
import { isDataJoin } from '../shared';
import BackButton from 'components/BackButton';
import styled from './index.module.less';

type TProps = {};

const DatasetJobDetail: FC<TProps> = function (props: TProps) {
  const { job_id } = useParams<{ job_id: string }>();
  const projectId = useGetCurrentProjectId();
  const [workFlowId, setWorkFlowId] = useState<ID>();
  const history = useHistory();
  const [jobBasicInfo, setJobBasicInfo] = useState(
    {} as {
      coordinatorId: ID;
      createTime: DateTime;
      startTime: DateTime;
      finishTime: DateTime;
      jobState: DatasetJobState;
    },
  );
  const jobDetailQuery = useQuery(
    ['fetch_dataset_jobDetail', projectId, job_id],
    () => fetchDatasetJobDetail(projectId!, job_id!),
    {
      refetchOnWindowFocus: false,
      retry: 2,
      enabled: Boolean(projectId && job_id),
      onSuccess: (data) => {
        const { workflow_id, coordinator_id, created_at, started_at, finished_at, state } =
          data.data || {};
        setJobBasicInfo({
          coordinatorId: coordinator_id,
          createTime: created_at,
          startTime: started_at,
          finishTime: finished_at,
          jobState: state,
        });
        setWorkFlowId(workflow_id);
      },
    },
  );
  const jobDetail = useMemo(() => {
    if (!jobDetailQuery.data) {
      return {};
    }
    return jobDetailQuery.data.data;
  }, [jobDetailQuery.data]);
  const isJoin = isDataJoin(jobDetailQuery.data?.data.kind);
  const globalConfigs = useMemo(() => {
    if (!jobDetailQuery.data) {
      return {};
    }
    return get(jobDetailQuery.data, 'data.global_configs.global_configs');
  }, [jobDetailQuery.data]);

  const backToList = () => {
    history.goBack();
  };

  return (
    <SharedPageLayout title={<BackButton onClick={backToList}>任务详情</BackButton>}>
      <JobTitle
        id={job_id}
        data={jobDetail as DatasetJob}
        onStop={jobDetailQuery.refetch}
        onDelete={backToList}
      />
      <JobBasicInfo {...jobBasicInfo} />
      <div className={styled.flex_container}>
        <TaskDetail
          middleJump={false}
          datasetJobId={job_id}
          isShowRatio={isJoin}
          onNodeClick={(node, datasetMapper = {}) => {
            if (node.type === NodeType.DATASET_PROCESSED) {
              const datasetInfo = datasetMapper[node?.data?.dataset_uuid ?? ''];
              datasetInfo &&
                datasetInfo.id &&
                history.push(
                  `/datasets/processed/detail/${datasetInfo.id}/${DatasetDetailSubTabs.PreviewData}`,
                );
            }
          }}
          // TODO: pass error message when state_frontend = DatasetStateFront.FAILED,
          errorMessage=""
          // TODO: confirm the dataset is processed or not by the state of job
          isProcessedDataset={true}
        />
        <JobParamsPanel globalConfigs={globalConfigs} />
      </div>
      <WorkFlowPods workFlowId={workFlowId} />
    </SharedPageLayout>
  );
};

export default DatasetJobDetail;
