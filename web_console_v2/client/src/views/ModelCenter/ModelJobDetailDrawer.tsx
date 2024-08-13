import React, { useState, useMemo } from 'react';
import dayjs from 'dayjs';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';

import { fetchModelJobDetail_new } from 'services/modelCenter';
import {
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantList,
  useGetCurrentPureDomainName,
} from 'hooks';

import { formatJSONValue } from 'shared/helpers';
import { formatTimestamp } from 'shared/date';
import {
  ALGORITHM_TYPE_LABEL_MAPPER,
  isNNAlgorithm,
  isTreeAlgorithm,
  TRAIN_ROLE,
} from 'views/ModelCenter/shared';
import { CONSTANTS } from 'shared/constants';

import { Drawer, Popover, Table, Button, Space, Tabs, Tag } from '@arco-design/web-react';
import { LabelStrong } from 'styles/elements';
import PropertyList from 'components/PropertyList';
import BackButton from 'components/BackButton';
import CodeEditor from 'components/CodeEditor';
import CountTime from 'components/CountTime';
import StateIndicator from 'components/StateIndicator';
import ReportResult from './ReportResult';
import InstanceInfo from './InstanceInfo';

import { DrawerProps } from '@arco-design/web-react/es/Drawer';
import { WorkflowState } from 'typings/workflow';
import AlgorithmDrawer from 'components/AlgorithmDrawer';
import { fetchPodLogs, fetchJobById } from 'services/workflow';
import { Pod, JobState } from 'typings/job';
import WhichAlgorithm from 'components/WhichAlgorithm';
import { ModelJob, ModelJobStatus } from 'typings/modelCenter';
import ResourceConfigTable from './ResourceConfigTable';
import { EnumAlgorithmProjectType } from 'typings/algorithm';
import { getDefaultVariableValue } from 'shared/modelCenter';
import { getModelJobStatus, LABEL_MAPPER } from './shared';

import './index.less';
import { fetchAlgorithmByUuid } from 'services/algorithm';
import { fetchDataBatchById } from 'services/dataset';

const { TabPane } = Tabs;
interface Props extends DrawerProps {
  /** Model job id */
  id: ID;
  pod?: Pod;
  showCodeEditorBackBtn?: boolean;
  datasetBatchType?: 'day' | 'hour';
}
type ButtonProps = Omit<Props, 'visible'> & {
  text?: string;
  btnDisabled?: boolean;
};

const getPropertyList = (algorithmType?: EnumAlgorithmProjectType) => {
  if (!algorithmType) {
    return [];
  }

  return [
    {
      text: '联邦类型',
      key: 'algorithm_type',
      render(_: any, job?: ModelJob) {
        return ALGORITHM_TYPE_LABEL_MAPPER[job?.algorithm_type || 'NN_VERTICAL'];
      },
    },
    isNNAlgorithm(algorithmType)
      ? {
          text: '算法',
          render(value: any) {
            const {
              algorithmProjectId,
              algorithmId,
              config = [],
              algorithmUuid,
              algorithmProjectUuid,
              participantId,
            } = JSON.parse(value?.algorithm?.value || '{}');
            return (
              <AlgorithmDrawer.Button
                algorithmProjectId={algorithmProjectId}
                algorithmId={algorithmId}
                parameterVariables={config}
                algorithmProjectUuid={algorithmProjectUuid}
                algorithmUuid={algorithmUuid}
                participantId={participantId}
              >
                <button className="custom-text-button">
                  <WhichAlgorithm
                    id={algorithmId}
                    uuid={algorithmUuid}
                    participantId={participantId}
                  />
                </button>
              </AlgorithmDrawer.Button>
            );
          },
        }
      : { key: 'loss_type', text: '损失函数类型' },
    {
      key: 'role',
      text: '训练角色',
      render(configMap: any) {
        const role = configMap?.role?.value;
        return role === TRAIN_ROLE.LEADER ? '标签方' : '特征方';
      },
    },
    {
      text: '数据集',
      render(_: any, job?: ModelJob) {
        const datasetName: string | undefined = job?.dataset_name ?? job?.intersection_dataset_name;
        return datasetName ? (
          <Link to={`/datasets/processed/detail/${job?.dataset_id}/dataset_job_detail`}>
            {datasetName}
          </Link>
        ) : (
          CONSTANTS.EMPTY_PLACEHOLDER
        );
      },
    },
    {
      key: 'dataset_batch_name',
      text: '数据批次',
      render(configMap: any, job?: ModelJob) {
        const datasetBatchName = configMap?.dataset_batch_name?.value;
        return datasetBatchName && job?.data_batch_id ? (
          <Link to={`/datasets/processed/detail/${job?.dataset_id}/data_batch`}>
            {datasetBatchName}
          </Link>
        ) : (
          CONSTANTS.EMPTY_PLACEHOLDER
        );
      },
    },
    {
      text: '资源配置',
      render(_: any, job?: ModelJob) {
        return (
          job && (
            <ResourceConfigTable.Button
              job={job}
              popoverProps={{ position: 'br', style: { maxWidth: 440, width: 440 } }}
            />
          )
        );
      },
    },
    {
      text: '参数配置',
      render(_: any, job?: ModelJob) {
        let keyList: string[] = [];

        switch (algorithmType) {
          case EnumAlgorithmProjectType.NN_VERTICAL:
            keyList = [
              'image',
              'data_source',
              'epoch_num',
              'verbosity',
              'shuffle_data_block',
              'save_checkpoint_secs',
              'save_checkpoint_steps',
              'load_checkpoint_filename',
              'load_checkpoint_filename_with_path',
              'sparse_estimator',
              'load_model_name',
            ];
            break;
          case EnumAlgorithmProjectType.NN_HORIZONTAL:
            keyList = ['epoch_num', 'verbosity', 'image', 'steps_per_sync', 'data_path'];
            break;
          case EnumAlgorithmProjectType.TREE_VERTICAL:
            keyList = [
              'learning_rate',
              'max_iters',
              'max_depth',
              'l2_regularization',
              'max_bins',
              'num_parallel',
              // 高级参数
              'image',
              'data_source',
              'file_ext',
              'file_type',
              'enable_packing',
              'ignore_fields',
              'cat_fields',
              'send_scores_to_follower',
              'send_metrics_to_follower',
              'verify_example_ids',
              'verbosity',
              'no_data',
              'label_field',
              'load_model_name',
              'load_model_path',
            ];
            break;
        }

        const textList = keyList.map((key) => {
          const value = getDefaultVariableValue(job as any, key);
          return {
            key: LABEL_MAPPER[key],
            value: value !== '' ? value : CONSTANTS.EMPTY_PLACEHOLDER,
          };
        });
        const table = (
          <Table
            className="custom-table"
            size="small"
            showHeader={false}
            columns={[
              { dataIndex: 'key', title: '' },
              { dataIndex: 'value', title: '' },
            ]}
            scroll={{
              y: 500,
            }}
            border={false}
            borderCell={false}
            pagination={false}
            data={textList}
          />
        );
        return (
          <Popover
            popupHoverStay={true}
            content={table}
            position="br"
            className={'params-popover-padding'}
          >
            <button className="custom-text-button">{'查看'}</button>
          </Popover>
        );
      },
    },
    {
      render(_: any, job?: ModelJob) {
        return job?.started_at && formatTimestamp(job.started_at);
      },
      key: 'started_at',
      text: '开始时间',
    },
    {
      key: 'stopped_at',
      text: '结束时间',
      render(_: any, job?: ModelJob) {
        return job?.stopped_at && formatTimestamp(job.stopped_at);
      },
    },
    {
      render(_: any, job?: ModelJob) {
        if (!job) {
          return CONSTANTS.EMPTY_PLACEHOLDER;
        }
        const { state, stopped_at, started_at } = job;
        const { RUNNING, STOPPED, COMPLETED, FAILED } = WorkflowState;
        const isRunning = state === RUNNING;
        const isStopped = [STOPPED, COMPLETED, FAILED].includes(state);
        let runningTime = 0;

        if (isRunning || isStopped) {
          runningTime = isStopped ? stopped_at! - started_at! : dayjs().unix() - started_at!;
        }

        return job ? <CountTime time={runningTime} isStatic={!isRunning} /> : 0;
      },
      text: '运行时长',
    },
    {
      text: '输出模型',
      render(_: any, job?: ModelJob) {
        if (!job) {
          return CONSTANTS.EMPTY_PLACEHOLDER;
        }

        return job.output_models[0]?.name;
      },
    },
  ];
};

function ModelJobDetailDrawer({
  id,
  visible,
  pod,
  onCancel,
  showCodeEditorBackBtn = true,
  title = '事件详情',
  datasetBatchType,
  ...restProps
}: Props) {
  const projectId = useGetCurrentProjectId();
  const myPureDomainName = useGetCurrentPureDomainName();
  const participantList = useGetCurrentProjectParticipantList();
  const [selectParticipant, setSelectParticipant] = useState<string>(myPureDomainName);
  const [metricIsPublic, setMetricIsPublic] = useState(false);
  const modelJobDetailQuery = useQuery(
    ['fetchModelJobDetail', id],
    () => {
      return fetchModelJobDetail_new(projectId!, id);
    },
    {
      enabled: Boolean(visible && id),
      retry: 2,
      refetchOnWindowFocus: false,
      onSuccess: (res) => {
        const { metric_is_public } = res.data;
        setMetricIsPublic(!!metric_is_public);
      },
    },
  );

  const modelJobDetail = useMemo(() => {
    return modelJobDetailQuery.data?.data;
  }, [modelJobDetailQuery.data?.data]);

  const datasetBatchDetailQuery = useQuery(
    ['fetchDatasetBatchDetail'],
    () => fetchDataBatchById(modelJobDetail?.dataset_id!, modelJobDetail?.data_batch_id!),
    {
      enabled: Boolean(modelJobDetail?.dataset_id && modelJobDetail?.data_batch_id),
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const datasetBatchDetail = useMemo(() => {
    if (!modelJobDetail?.data_batch_id) {
      return undefined;
    }
    return datasetBatchDetailQuery.data?.data;
  }, [datasetBatchDetailQuery.data?.data, modelJobDetail?.data_batch_id]);
  const isOldModelJob = useMemo(() => {
    return !modelJobDetailQuery.data?.data.global_config;
  }, [modelJobDetailQuery.data?.data.global_config]);

  const algorithmDetailQuery = useQuery(
    [
      'fetchAlgorithmDetail',
      projectId,
      modelJobDetail?.global_config?.global_config?.[selectParticipant]?.algorithm_uuid,
    ],
    () =>
      fetchAlgorithmByUuid(
        projectId!,
        modelJobDetail?.global_config?.global_config?.[selectParticipant]?.algorithm_uuid!,
      ),
    {
      enabled: Boolean(
        projectId &&
          modelJobDetail?.global_config?.global_config?.[selectParticipant]?.algorithm_uuid,
      ),
      refetchOnWindowFocus: false,
    },
  );

  const algorithmDetail = useMemo(() => {
    return algorithmDetailQuery.data?.data;
  }, [algorithmDetailQuery.data?.data]);

  const { data: jobInstanceDetail } = useQuery(
    ['workflow', modelJobDetail?.job_id],
    () => fetchJobById(modelJobDetail?.job_id as number).then((res) => res.data),
    {
      enabled: Boolean(projectId) && Boolean(modelJobDetail?.job_id),
    },
  );
  const errorMessage = useMemo(() => {
    return jobInstanceDetail?.state !== JobState.COMPLETED &&
      jobInstanceDetail?.error_message &&
      (jobInstanceDetail?.error_message?.app ||
        JSON.stringify(jobInstanceDetail?.error_message?.pods) !== '{}')
      ? JSON.stringify(jobInstanceDetail.error_message)
      : '';
  }, [jobInstanceDetail]);

  const { data: podLog } = useQuery(
    ['model-detail-drawer-pod-log', pod?.name],
    () => {
      return fetchPodLogs(pod?.name!, modelJobDetail?.job_id!, { maxLines: 5000 }).then(
        (res) => res.data,
      );
    },
    { enabled: Boolean(pod?.name && modelJobDetail?.job_id), refetchOnWindowFocus: false },
  );
  const configValueMap: { [key: string]: any } = useMemo(() => {
    if (!modelJobDetail) {
      return {};
    }

    return modelJobDetail.config?.job_definitions?.[0].variables.reduce((acc, cur) => {
      acc[cur.name] = { ...cur };
      return acc;
    }, {} as { [key: string]: any });
  }, [modelJobDetail]);

  const displayedProps = useMemo(() => {
    if (!modelJobDetail?.config) {
      return [];
    }
    let valueMap: { [key: string]: any } = {};
    if (isOldModelJob) {
      valueMap = configValueMap;
    } else {
      valueMap =
        modelJobDetail?.global_config?.global_config?.[selectParticipant]?.variables.reduce(
          (acc, cur) => {
            acc[cur.name] = { ...cur };
            return acc;
          },
          {} as { [key: string]: any },
        ) ?? {};
      const algorithmId = algorithmDetail?.id ? algorithmDetail?.id : null;
      const participantId = algorithmDetail?.participant_id ? algorithmDetail?.participant_id : 0;
      valueMap['algorithm'] = {
        value: JSON.stringify({
          algorithmId: algorithmId,
          algorithmUuid: algorithmDetail?.uuid,
          algorithmProjectId: algorithmDetail?.algorithm_project_id,
          algorithmProjectUuid: algorithmDetail?.algorithm_project_uuid,
          participantId: participantId,
        }),
      };
      valueMap['dataset_batch_name'] = {
        value: datasetBatchDetail?.name,
      };
    }

    return [
      ...getPropertyList(modelJobDetail?.algorithm_type).map((item) => {
        const { text, key, render } = item;

        return {
          label: text ?? key ?? CONSTANTS.EMPTY_PLACEHOLDER,
          value:
            typeof render === 'function'
              ? render(valueMap, modelJobDetail)
              : key && valueMap[key]
              ? valueMap[key].value
              : CONSTANTS.EMPTY_PLACEHOLDER,
        };
      }),
    ];
  }, [
    modelJobDetail,
    isOldModelJob,
    configValueMap,
    selectParticipant,
    algorithmDetail?.id,
    algorithmDetail?.participant_id,
    algorithmDetail?.uuid,
    algorithmDetail?.algorithm_project_id,
    algorithmDetail?.algorithm_project_uuid,
    datasetBatchDetail?.name,
  ]);

  const refreshModelJobDetail = () => {
    modelJobDetailQuery.refetch();
  };

  function renderInfoLayout() {
    return (
      <>
        {isOldModelJob ? (
          <LabelStrong isBlock={true}>训练配置</LabelStrong>
        ) : (
          <Space>
            <LabelStrong isBlock={true}>训练配置</LabelStrong>
            <Tabs
              className="custom-tabs"
              type="text"
              activeTab={selectParticipant}
              onChange={setSelectParticipant}
            >
              <TabPane title={'本方'} key={myPureDomainName} />
              {participantList.map((participant) => {
                return <TabPane title={participant.name} key={participant.pure_domain_name} />;
              })}
            </Tabs>
          </Space>
        )}

        <PropertyList properties={displayedProps} cols={4} />
        <ReportResult
          onSwitch={refreshModelJobDetail}
          metricIsPublic={metricIsPublic}
          id={id}
          title={'训练报告'}
          algorithmType={modelJobDetail?.algorithm_type}
          isNNAlgorithm={modelJobDetail ? isNNAlgorithm(modelJobDetail?.algorithm_type) : false}
          hideConfusionMatrix={
            modelJobDetail &&
            isTreeAlgorithm(modelJobDetail.algorithm_type) &&
            configValueMap.loss_type === 'mse'
          }
        />
        <div className="left-container">
          <LabelStrong isBlock={true}>实例信息</LabelStrong>
          <Popover
            trigger="hover"
            position="br"
            content={
              <span>
                <div className="pop-title">工作流</div>
                <Link
                  className="styled-link"
                  to={`/workflow-center/workflows/${modelJobDetail?.workflow_id}`}
                >
                  label_jump_to_workflow
                </Link>
                <div className="pop-title">工作流 ID</div>
                <div className="pop-content">{modelJobDetail?.workflow_id}</div>
              </span>
            }
          >
            <Button className="right-button" size="mini" type="text">
              更多信息
            </Button>
          </Popover>
        </div>

        {modelJobDetail?.job_id ? <InstanceInfo id={id} jobId={modelJobDetail?.job_id} /> : null}
      </>
    );
  }
  function renderCodeEditorLayout() {
    return (
      <>
        {showCodeEditorBackBtn && (
          <div className="header">
            <BackButton onClick={onCancel}>返回</BackButton>
          </div>
        )}
        <CodeEditor
          language="json"
          isReadOnly={true}
          theme="grey"
          height="calc(100vh - 119px)" // 55(drawer header height) + 16*2(content padding) + 32(header height)
          value={formatJSONValue(podLog?.join('\n') ?? CONSTANTS.EMPTY_PLACEHOLDER)}
        />
      </>
    );
  }

  return (
    <Drawer
      unmountOnExit={true}
      placement="right"
      title={
        <Space>
          {modelJobDetail?.name}
          <StateIndicator
            tag={true}
            tip={errorMessage}
            position="bottom"
            {...getModelJobStatus(modelJobDetail?.status as ModelJobStatus, {
              isHideAllActionList: true,
            })}
          />
          {modelJobDetail?.auto_update && (
            <Tag color={datasetBatchType === 'hour' ? 'arcoblue' : 'purple'}>
              {datasetBatchType === 'hour' ? '小时级' : '天级'}
            </Tag>
          )}
        </Space>
      }
      closable={true}
      width="1000px"
      visible={visible}
      onCancel={onCancel}
      {...restProps}
    >
      <div className="drawer-content">{pod ? renderCodeEditorLayout() : renderInfoLayout()}</div>
    </Drawer>
  );
}

export function _Button({ text = '详情', btnDisabled, children, ...restProps }: ButtonProps) {
  const [visible, setVisible] = useState(false);
  return (
    <>
      {children ? (
        <span onClick={() => setVisible(true)}>{children}</span>
      ) : (
        <button
          disabled={btnDisabled}
          type="button"
          className="custom-text-button"
          onClick={() => setVisible(true)}
        >
          {text}
        </button>
      )}
      <ModelJobDetailDrawer visible={visible} {...restProps} onCancel={() => setVisible(false)} />
    </>
  );
}

ModelJobDetailDrawer.Button = _Button;

export default ModelJobDetailDrawer;
