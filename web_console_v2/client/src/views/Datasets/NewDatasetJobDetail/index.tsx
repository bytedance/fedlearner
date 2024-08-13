import React, { FC, useMemo, useState, useRef } from 'react';
import { Tabs, Message } from '@arco-design/web-react';
import SharedPageLayout from 'components/SharedPageLayout';
import TaskDetail, { NodeType } from '../TaskDetail';
import { useParams } from 'react-router-dom';
import JobTitle from './JobTitle';
import { useQuery } from 'react-query';
import { fetchDatasetJobDetail, fetchDatasetDetail, fetchDatasetList } from 'services/dataset';
import { useGetCurrentProjectId } from 'hooks';
import { DatasetJob, DatasetKindLabel, DatasetKindLabelCapitalMapper } from 'typings/dataset';
import JobBasicInfo from './JobBasicInfo';
import JobStageDetail from './JobStageDetail';
import { DatasetDetailSubTabs } from '../DatasetDetail';
import { useHistory, Route, Redirect } from 'react-router';
import BackButton from 'components/BackButton';
import {
  isDataJoin,
  isDataExport,
  FILTER_OPERATOR_MAPPER,
  filterExpressionGenerator,
} from '../shared';
import { useGetCurrentDomainName } from 'hooks';
import styled from './index.module.less';

const { TabPane } = Tabs;

type TProps = {};

export enum JobDetailSubTabs {
  TaskProcess = 'process',
  TaskList = 'list',
}

const DatasetJobDetail: FC<TProps> = function (props: TProps) {
  const { job_id, subtab, dataset_id } = useParams<{
    job_id: string;
    subtab: string;
    dataset_id: string;
  }>();
  const currentDomainName = useGetCurrentDomainName();
  const projectId = useGetCurrentProjectId();
  const history = useHistory();
  const jobStageDetailRef = useRef<any>();
  const [activeTab, setActiveTab] = useState(subtab || JobDetailSubTabs.TaskProcess);
  const [jobBasicInfo, setJobBasicInfo] = useState(
    {} as {
      coordinatorId: ID;
      createTime: DateTime;
      creator_username: string;
    },
  );
  // ======= Dataset query ============
  const query = useQuery(['fetchDatasetDetail', dataset_id], () => fetchDatasetDetail(dataset_id), {
    refetchOnWindowFocus: false,
    enabled: Boolean(dataset_id),
    onError(e: any) {
      Message.error(e.message);
    },
  });
  // 表示任务的是是否是原始数据集， 用于后续跳转详情页
  const isProcessed = Boolean(
    DatasetKindLabelCapitalMapper[DatasetKindLabel.PROCESSED] === query.data?.data.dataset_kind,
  );
  const jobDetailQuery = useQuery(
    ['fetch_dataset_jobDetail', projectId, job_id],
    () => fetchDatasetJobDetail(projectId!, job_id!),
    {
      refetchOnWindowFocus: false,
      retry: 2,
      enabled: Boolean(projectId && job_id),
      onSuccess: (data) => {
        const { coordinator_id, created_at, creator_username } = data.data || {};
        setJobBasicInfo({
          coordinatorId: coordinator_id,
          createTime: created_at,
          creator_username,
        });
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
  const isExport = isDataExport(jobDetailQuery.data?.data.kind);
  // 导出任务的导入数据集uuid, 服务端担心直接加导入数据集的id会有问题？
  const inportDatasetUuid = useMemo(() => {
    const rawDatasetObject = jobDetailQuery.data?.data?.global_configs?.global_configs ?? {};
    let inportDatasetUuid: string = '';
    Object.keys(rawDatasetObject).forEach((key, index) => {
      const rawDatasetInfo = rawDatasetObject[key];
      if (currentDomainName.indexOf(key) > -1) {
        inportDatasetUuid = rawDatasetInfo.dataset_uuid;
      }
    });
    return inportDatasetUuid;
  }, [jobDetailQuery, currentDomainName]);

  const datasetListQuery = useQuery(
    ['fetchDatasetList', inportDatasetUuid],
    () =>
      fetchDatasetList({
        filter: filterExpressionGenerator(
          {
            uuid: inportDatasetUuid,
          },
          FILTER_OPERATOR_MAPPER,
        ),
      }),
    {
      enabled: Boolean(inportDatasetUuid) && Boolean(isExport),
      refetchOnWindowFocus: false,
      retry: 2,
    },
  );

  const importDatasetId = useMemo(() => {
    if (!datasetListQuery.data?.data) return null;
    return datasetListQuery.data?.data?.[0]?.id;
  }, [datasetListQuery]);

  const backToList = () => {
    history.goBack();
  };
  /** IF no subtab be set, defaults to preview */
  if (!subtab) {
    return (
      <Redirect
        to={`/datasets/${dataset_id}/new/job_detail/${job_id}/${JobDetailSubTabs.TaskProcess}`}
      />
    );
  }

  return (
    <SharedPageLayout
      title={<BackButton onClick={backToList}>任务详情</BackButton>}
      cardPadding={0}
    >
      <JobTitle id={job_id} data={jobDetail as DatasetJob} onStop={onStop} onDelete={backToList} />
      <JobBasicInfo {...jobBasicInfo} />
      <Tabs activeTab={activeTab} onChange={onSubtabChange} className={styled.data_detail_tab}>
        <TabPane
          className={styled.data_detail_tab_pane}
          title="任务流程"
          key={JobDetailSubTabs.TaskProcess}
        />
        <TabPane
          className={styled.data_detail_tab_pane}
          title="任务列表"
          key={JobDetailSubTabs.TaskList}
        />
      </Tabs>
      <Route
        path={`/datasets/:dataset_id/new/job_detail/:job_id/${JobDetailSubTabs.TaskProcess}`}
        exact
        render={(props) => {
          return (
            <TaskDetail
              className={styled.data_job_task_detail}
              middleJump={false}
              datasetJobId={job_id}
              isShowTitle={false}
              isShowRatio={!jobDetailQuery.data?.data?.has_stages}
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
          );
        }}
      />
      <Route
        path={`/datasets/:dataset_id/new/job_detail/:job_id/${JobDetailSubTabs.TaskList}`}
        exact
        render={(props) => {
          return (
            <JobStageDetail
              ref={jobStageDetailRef}
              isProcessed={isProcessed}
              isJoin={isJoin}
              isExport={isExport}
              importDatasetId={importDatasetId}
            />
          );
        }}
      />
    </SharedPageLayout>
  );

  function onSubtabChange(val: string) {
    setActiveTab(val as JobDetailSubTabs);
    history.replace(`/datasets/${dataset_id}/new/job_detail/${job_id}/${val}`);
  }

  function onStop() {
    jobDetailQuery.refetch();
    jobStageDetailRef.current.refetch();
  }
};

export default DatasetJobDetail;
