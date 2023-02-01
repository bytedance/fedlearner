import React, { useState } from 'react';
import { generatePath, Redirect, useHistory, useParams } from 'react-router';
import { Link } from 'react-router-dom';
import { Grid, Tabs, Space, Typography, Message, Popover, Button } from '@arco-design/web-react';
import { IconShareInternal } from '@arco-design/web-react/icon';
import { useQuery } from 'react-query';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';
import GridRow from 'components/_base/GridRow';
import MoreActions from 'components/MoreActions';
import PropertyList from 'components/PropertyList';
import StateIndicator from 'components/StateIndicator';
import AlgorithmType from 'components/AlgorithmType';
import CountTime from 'components/CountTime';
import { getFullModelJobDownloadHref } from 'services/modelCenter';
import { fetchModelDetail_new, fetchModelJob_new } from 'services/modelCenter';
import { useGetCurrentProjectId } from 'hooks';

import { Avatar, deleteEvaluationJob, getModelJobStatus } from '../../shared';
import routes, { ModelEvaluationDetailParams, ModelEvaluationDetailTab } from '../../routes';
import ReportResult from '../../ReportResult';
import InstanceInfo from '../../InstanceInfo';
import WhichRole from '../WhichRole';
import { formatTimestamp } from 'shared/date';
import ResourceConfigTable from 'views/ModelCenter/ResourceConfigTable';
import ModelJobDetailDrawer from 'views/ModelCenter/ModelJobDetailDrawer';
import { TIME_INTERVAL, CONSTANTS } from 'shared/constants';
import { ModelJobState, ModelJobStatus } from 'typings/modelCenter';
import request from 'libs/request';
import { isNNAlgorithm } from 'views/ModelCenter/shared';

import './index.less';

const ModelEvaluation: React.FC = () => {
  const params = useParams<ModelEvaluationDetailParams>();
  const history = useHistory();
  const projectId = useGetCurrentProjectId();
  const [metricIsPublic, setMetricIsPublic] = useState(false);
  const detailQuery = useQuery(
    ['model-valuation-detail-page-query', params.id, projectId],
    () => fetchModelJob_new(projectId!, params.id).then((res) => res.data),
    {
      enabled: Boolean(projectId),
      refetchInterval: TIME_INTERVAL.LIST,
      onSuccess: (res) => {
        const { metric_is_public } = res;
        setMetricIsPublic(!!metric_is_public);
      },
    },
  );

  const { data: detail } = detailQuery;
  const { data: relativeModelData } = useQuery(
    ['model_valuation-detail-relative-model', detail?.model_id, projectId],
    () => fetchModelDetail_new(projectId!, detail?.model_id!).then((res) => res.data),
    {
      enabled: Boolean(detail?.model_id && projectId),
    },
  );

  const isModelEvaluation = params.module === 'model-evaluation';
  const isJobRunning = detail?.state === ModelJobState.RUNNING;

  const propertyList = [
    {
      label: '运行状态',
      value: detail ? (
        <StateIndicator {...getModelJobStatus(detail.status, { isHideAllActionList: true })} />
      ) : null,
    },
    {
      label: '发起方',
      value: <WhichRole job={detail} />,
    },
    {
      label: '创建者',
      value: detail?.creator_username || '-',
    },
    {
      label: '模型',
      value: relativeModelData?.model_job_id ? (
        <ModelJobDetailDrawer.Button
          id={relativeModelData?.model_job_id}
          text={relativeModelData?.name}
          title={
            <Space>
              {relativeModelData?.name}
              <StateIndicator
                tag={true}
                {...getModelJobStatus(detail?.status as ModelJobStatus, {
                  isHideAllActionList: true,
                })}
              />
            </Space>
          }
        />
      ) : (
        CONSTANTS.EMPTY_PLACEHOLDER
      ),
    },
    {
      label: '数据集',
      value:
        detail?.dataset_name ?? detail?.intersection_dataset_name ? (
          <Link to={`/datasets/processed/detail/${detail?.dataset_id}/dataset_job_detail`}>
            {detail?.dataset_name ?? detail?.intersection_dataset_name}
          </Link>
        ) : (
          CONSTANTS.EMPTY_PLACEHOLDER
        ),
    },
    {
      label: '资源配置',
      value: detail && (
        <ResourceConfigTable.Button
          job={detail}
          popoverProps={{ position: 'bl', style: { maxWidth: 500, width: 500 } }}
        />
      ),
    },
    {
      label: '创建时间',
      value: detail?.created_at ? formatTimestamp(detail?.created_at) : CONSTANTS.EMPTY_PLACEHOLDER,
    },
    {
      label: '开始时间',
      value: detail?.started_at && formatTimestamp(detail.started_at),
    },
    {
      label: '结束时间',
      value:
        detail?.state === ModelJobState.COMPLETED && detail?.stopped_at
          ? formatTimestamp(detail.stopped_at)
          : CONSTANTS.EMPTY_PLACEHOLDER,
    },
    {
      label: '运行时长',
      value:
        detail?.started_at || detail?.stopped_at ? (
          <CountTime
            time={
              isJobRunning
                ? Math.floor(Date.now() / 1000) - (detail?.started_at ?? 0)
                : (detail?.stopped_at ?? 0) - (detail?.started_at ?? 0)
            }
            isStatic={!isJobRunning}
          />
        ) : (
          CONSTANTS.EMPTY_PLACEHOLDER
        ),
    },
  ];

  const refreshModelJobDetail = () => {
    detailQuery.refetch();
  };

  return (
    <SharedPageLayout
      cardPadding={0}
      title={
        <BackButton onClick={() => goToListPage()}>
          {isModelEvaluation ? '模型评估' : '离线预测'}
        </BackButton>
      }
    >
      <div className="padding-container-card">
        <Grid.Row align="center" justify="space-between">
          <GridRow gap="12" style={{ maxWidth: '85%' }}>
            <Avatar data-name={detail?.name} />
            <div>
              <Space>
                <h3 className="eval-name">{detail?.name}</h3>
                {detail && <AlgorithmType type={detail.algorithm_type} />}
              </Space>
              <small className="eval-comment">{detail?.comment}</small>
            </div>
          </GridRow>

          <GridRow>
            <MoreActions
              actionList={[
                {
                  label: '删除',
                  disabled: !projectId || !detail,
                  danger: true,
                  onClick: async () => {
                    if (projectId && detail) {
                      try {
                        const res = await deleteEvaluationJob(
                          projectId,
                          detail,
                          params.module,
                        ).then();
                        if (res) {
                          goToListPage(true);
                        }
                      } catch (e) {}
                    }
                  },
                },
              ]}
            />
          </GridRow>
        </Grid.Row>
        <div>
          <PropertyList cols={5} colProportions={[1, 1, 1, 1, 1]} properties={propertyList} />
        </div>
      </div>
      {!params.tab && <Redirect to={getTabPath(ModelEvaluationDetailTab.Result)} />}
      {params.module === 'model-evaluation' && (
        <>
          <Tabs
            defaultActiveTab={params.tab}
            onChange={(tab) => history.push(getTabPath(tab))}
            style={{ marginBottom: 0 }}
          >
            <Tabs.TabPane title={'评估结果'} key={ModelEvaluationDetailTab.Result} />
            <Tabs.TabPane title={'实例信息'} key={ModelEvaluationDetailTab.Info} />
          </Tabs>
          <div className="padding-container-card padding-top-card">
            {params.tab === ModelEvaluationDetailTab.Result && (
              <ReportResult
                onSwitch={refreshModelJobDetail}
                metricIsPublic={metricIsPublic}
                id={params.id}
                isTraining={false}
                isNNAlgorithm={detail ? isNNAlgorithm(detail?.algorithm_type) : false}
                algorithmType={detail?.algorithm_type}
              />
            )}
            {params.tab === ModelEvaluationDetailTab.Info && detail?.job_id && (
              <>
                <InstanceInfo id={params.id} jobId={detail?.job_id} />
                <Popover
                  trigger="hover"
                  position="br"
                  content={
                    <>
                      <div className="pop-title">工作流</div>
                      <Link
                        className="styled-link"
                        to={`/workflow-center/workflows/${detail?.workflow_id}`}
                      >
                        点击查看工作流
                      </Link>
                      <div className="pop-title">工作流 ID</div>
                      <div className="pop-content">{detail?.workflow_id}</div>
                    </>
                  }
                >
                  <Button size="mini" type="text">
                    更多信息
                  </Button>
                </Popover>
              </>
            )}
          </div>
        </>
      )}
      {params.module === 'offline-prediction' && detail?.job_id && (
        <div className="padding-container-card padding-top-card">
          <div>
            <Typography.Text bold={true} className="custom-typography eval-section-title">
              预测结果
            </Typography.Text>
            <button className="custom-text-button" onClick={downloadDataset}>
              <IconShareInternal />
              结果数据集
            </button>
          </div>
          <div style={{ marginTop: 20 }}>
            <Typography.Text bold={true} className="custom-typography eval-section-title">
              实例信息
            </Typography.Text>
            <InstanceInfo id={params.id} jobId={detail?.job_id} style={{ marginTop: 0 }} />
          </div>
        </div>
      )}
    </SharedPageLayout>
  );

  function getTabPath(tab: string) {
    return generatePath(routes.ModelEvaluationDetail, {
      ...params,
      tab: tab as ModelEvaluationDetailTab,
    });
  }

  async function downloadDataset() {
    try {
      const tip = await request.download(getFullModelJobDownloadHref(projectId!, detail?.id!));
      tip && Message.info(tip);
    } catch (error) {
      Message.error(error.message);
    }
  }

  function goToListPage(isReplace = false) {
    history[isReplace ? 'replace' : 'push'](
      generatePath(routes.ModelEvaluationList, {
        module: params.module,
      }),
    );
  }
};

export default ModelEvaluation;
