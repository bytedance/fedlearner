/* istanbul ignore file */

import React, { FC, ReactNode, useMemo } from 'react';
import { generatePath, useHistory } from 'react-router-dom';

import { formatTimestamp } from 'shared/date';
import { TIME_INTERVAL } from 'shared/constants';

import { useQuery } from 'react-query';
import { fetchProjectPendingList } from 'services/algorithm';
import { fetchModelServingList_new } from 'services/modelServing';
import {
  fetchModelJobGroupList,
  fetchModelJobList_new,
  fetchPeerModelJobGroupDetail,
} from 'services/modelCenter';
import { fetchPendingProjectList } from 'services/project';

import { Message, Button, Popover, Tooltip } from '@arco-design/web-react';
import { Todo, Right } from 'components/IconPark';

import { Workflow } from 'typings/workflow';
import { ModelServing, ModelServingState } from 'typings/modelServing';
import { ModelJob, ModelJobGroup } from 'typings/modelCenter';
import { Algorithm } from 'typings/algorithm';

import newModelCenterRoutes, { ModelEvaluationModuleType } from 'views/ModelCenter/routes';
import { getCoordinateName, PENDING_PROJECT_FILTER_MAPPER } from 'views/Projects/shard';
import { filterExpressionGenerator } from 'views/Datasets/shared';
import { FILTER_MODEL_JOB_OPERATOR_MAPPER } from 'views/ModelCenter/shared';
import {
  useGetAppFlagValue,
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantList,
} from 'hooks';
import { APIResponse } from 'typings/app';
import { NotificationItem, NotificationType } from 'typings/trustedCenter';
import { fetchTrustedNotifications } from 'services/trustedCenter';
import { FilterOp } from 'typings/filter';
import { Project, ProjectStateType } from 'typings/project';
import { constructExpressionTree } from 'shared/filter';
import { FlagKey } from 'typings/flag';

import styles from './index.module.less';

const CUSTOM_CLASS_NAME = 'custom-popover';

export type Props<T = any> = {
  isLoading?: boolean;
  disabled?: boolean;
  list: T[];
  buttonText?: string;
  renderContent: (list: T[], options?: any) => ReactNode;
};

export type ApprovalProps<T = any> = Omit<Props<T>, 'renderContent'> & {
  title?: string;
  onClick?: (item?: T) => void;
  dateField?: string;
  creatorField?: string;
  contentField?: string;
  contentVerb?: string;
  contentSuffix?: string;
  contentPrefix?: string;
  renderContent?: (list: T[], options?: any) => ReactNode;
};

export type TrainModelProps<T = any> = Omit<ApprovalProps<T>, 'list'> & {};

export type EvaluationModelNewProps<T = any> = TrainModelProps<T> & {
  module: ModelEvaluationModuleType;
};

export type TrustedCenterProps<T = any> = Omit<ApprovalProps<T>, 'list'> & {};

function TodoPopover<T = any>({
  isLoading = false,
  disabled = false,
  list = [],
  buttonText = '',
  renderContent,
  ...restProps
}: Props<T>) {
  return (
    <>
      <Popover className={CUSTOM_CLASS_NAME} content={renderContent(list, restProps)} position="br">
        <Button
          className={styles.todo_button}
          loading={isLoading}
          icon={<Todo className={styles.icon_todo} />}
          disabled={disabled || list.length === 0}
          type={list.length ? 'primary' : 'default'}
        >
          {buttonText}
        </Button>
      </Popover>
    </>
  );
}

const RenderItem: FC<{ item: any; options?: any }> = ({ item, options }) => {
  const coordinatorName = getCoordinateName(item?.participants_info?.participants_map);
  const participantList = useGetCurrentProjectParticipantList();
  const participant = participantList.filter((item_) => item_?.id === item.coordinator_id);

  return (
    <div
      className={styles.overlay_item}
      onClick={(e) => {
        e.stopPropagation();
        options.onClick(item);
      }}
    >
      <div className={styles.overlay_item_header}>
        <span className={styles.label}>
          {coordinatorName || participant?.[0]?.name || participantList?.[0]?.name}
          {options.contentVerb ?? ' 发起了'}
        </span>
        <Tooltip content={`「${item[options.contentField]}」${options.contentSuffix || ''}`}>
          <span className={styles.label_strong}>
            {`「${item[options.contentField]}」`}
            {options.contentSuffix || ''}
          </span>
        </Tooltip>
      </div>
      <div>
        <span className={styles.label_tiny}>{formatTimestamp(item[options.dateField])}</span>
      </div>
      <Right className={styles.icon_right} />
    </div>
  );
};

function renderDefaultModelCenterContent(list: any, options?: any) {
  return (
    <div>
      <div className={styles.overlay_header}>
        <span className={styles.label}>{options.title}</span>
        <div className={styles.number_tag}>{list.length}</div>
      </div>
      {list.map((item: any) => (
        <RenderItem item={item} options={options} key={item.id} />
      ))}
    </div>
  );
}

function ModelCenter({
  renderContent = renderDefaultModelCenterContent,
  ...restProps
}: ApprovalProps) {
  return <TodoPopover renderContent={renderContent} {...restProps} />;
}

function EvaluationModelNew({
  dateField = 'created_at',
  contentField = 'name',
  module,
  ...restProps
}: EvaluationModelNewProps) {
  const history = useHistory();
  const projectId = useGetCurrentProjectId();
  const isPrediction = module === 'offline-prediction';
  const copywriting = isPrediction ? '预测' : '评估';

  const { isError, data: workflowListData, error, isFetching } = useQuery(
    ['todoPopover_model_evaluation_notice_list', projectId, module],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return Promise.resolve({ data: [] as ModelJob[] });
      }

      return fetchModelJobList_new(projectId, {
        filter: filterExpressionGenerator(
          { auth_status: ['PENDING'] },
          FILTER_MODEL_JOB_OPERATOR_MAPPER,
        ),
        types: isPrediction ? 'PREDICTION' : 'EVALUATION',
      });
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST, // auto refresh every 1.5 min
    },
  );

  if (isError && error) {
    Message.error((error as Error).message);
  }

  return (
    <ModelCenter
      isLoading={isFetching}
      list={workflowListData?.data || []}
      dateField={dateField}
      contentField={contentField}
      buttonText={`${workflowListData?.data.length || 0} 条待处理${copywriting}任务`}
      title={`待处理${copywriting}任务`}
      contentSuffix={`的${copywriting}任务`}
      onClick={onClick}
      {...restProps}
    />
  );

  function onClick(item: Workflow) {
    history.push(`/model-center/${module}/receiver/edit/${item.id}`);
  }
}

function AlgorithmManagement({
  dateField = 'created_at',
  creatorField = 'creator',
  contentField = 'name',
  ...restProps
}: TrainModelProps) {
  const history = useHistory();
  const projectId = useGetCurrentProjectId();

  const { isError, data: algorithmData, error, isFetching } = useQuery(
    ['algorithmReceiveList', projectId],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return Promise.resolve({ data: [] }) as APIResponse<Algorithm[]>;
      }
      return fetchProjectPendingList(projectId ?? 0);
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST, // auto refresh every 1.5 min
    },
  );

  if (isError && error) {
    Message.error((error as Error).message);
  }

  const todoList = algorithmData?.data || [];
  return (
    <ModelCenter
      isLoading={isFetching}
      list={todoList}
      dateField={dateField}
      contentField={contentField}
      buttonText={`${todoList.length} 条待处理算法消息`}
      title={'待处理算法任务'}
      contentVerb={'发布了'}
      contentSuffix={' 算法'}
      onClick={onClick}
      {...restProps}
    />
  );

  function onClick(item: Algorithm) {
    history.push(`/algorithm-management/acceptance/${item.id}`);
  }
}

function ModelServingNotice({
  dateField = 'created_at',
  creatorField = 'creator',
  contentField = 'name',
  ...restProps
}: TrainModelProps) {
  const history = useHistory();
  const projectId = useGetCurrentProjectId();

  const { isError, isFetching, data, error } = useQuery(
    ['fetchModelServingList', projectId],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return Promise.resolve({ data: [] }) as APIResponse<ModelServing[]>;
      }

      return fetchModelServingList_new(projectId);
    },

    {
      refetchInterval: TIME_INTERVAL.LIST,
    },
  );

  if (isError && error) {
    Message.error((error as Error).message);
  }

  const todoList = useMemo(() => {
    if (!data?.data) {
      return [];
    }

    return data.data.filter((item) => item.status === ModelServingState.WAITING_CONFIG);
  }, [data?.data]);

  return (
    <ModelCenter
      isLoading={isFetching}
      list={todoList}
      dateField={dateField}
      contentField={contentField}
      buttonText={`${todoList.length} 条待处理在线服务`}
      title={'待处理在线服务'}
      contentSuffix={' 的在线任务'}
      onClick={onClick}
      {...restProps}
    />
  );

  function onClick(item: ModelServing) {
    history.push(`/model-serving/create/receiver/${item.id}`);
  }
}

function NewTrainModel({
  dateField = 'created_at',
  contentField = 'name',
  ...restProps
}: TrainModelProps) {
  const history = useHistory();
  const projectId = useGetCurrentProjectId();

  const model_job_global_config_enabled = useGetAppFlagValue(
    FlagKey.MODEL_JOB_GLOBAL_CONFIG_ENABLED,
  );

  const { isError, data, error, isFetching } = useQuery<{
    data: ModelJobGroup[];
  }>(
    ['fetchModelJobGroupList', projectId],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return Promise.resolve({ data: [] });
      }
      return fetchModelJobGroupList(projectId!, {
        filter: constructExpressionTree([
          {
            field: 'configured',
            op: FilterOp.EQUAL,
            bool_value: false,
          },
        ]),
      });
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST, // auto refresh every 1.5 min
    },
  );

  if (isError && error) {
    Message.error((error as Error).message);
  }

  const todoList = useMemo(() => {
    if (!data) {
      return [];
    }
    const list = data.data || [];

    return list;
  }, [data]);

  return (
    <ModelCenter
      isLoading={isFetching}
      list={todoList}
      dateField={dateField}
      contentField={contentField}
      buttonText={`${todoList.length} 条待处理模型训练`}
      title={'待处理模型训练'}
      contentSuffix={'的模型训练'}
      onClick={onClick}
      {...restProps}
    />
  );

  async function onClick(item: ModelJobGroup) {
    let isOldModelGroup = true;
    if (model_job_global_config_enabled) {
      try {
        const res = await fetchPeerModelJobGroupDetail(projectId!, item.id, item.coordinator_id!);
        const modelGroupDetail = res.data;
        isOldModelGroup = Boolean(modelGroupDetail?.config?.job_definitions?.length);
      } catch (error) {
        Message.error('获取模型训练作业详情失败！');
        return;
      }
    }
    model_job_global_config_enabled && !isOldModelGroup
      ? history.push(
          generatePath(newModelCenterRoutes.ModelTrainCreateCentralization, {
            role: 'receiver',
            id: item.id,
          }),
        )
      : history.push(
          generatePath(newModelCenterRoutes.ModelTrainCreate, {
            role: 'receiver',
            action: 'create',
            id: item.id,
          }),
        );
  }
}

function TrustedCenter({
  dateField = 'created_at',
  creatorField = 'coordinator_id',
  contentField = 'name',
  ...restProps
}: TrustedCenterProps) {
  const history = useHistory();
  const projectId = useGetCurrentProjectId();

  const { isError, data, error, isFetching } = useQuery<{ data: NotificationItem[] }>(
    ['fetchTrustedNotifications', projectId],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return Promise.resolve({ data: [] });
      }
      return fetchTrustedNotifications(projectId!);
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST, // auto refresh every 1.5 min
    },
  );

  if (isError && error) {
    Message.error((error as Error).message);
  }

  const todoList = useMemo(() => {
    if (!data) {
      return [];
    }

    const list = data.data || [];

    return list;
  }, [data]);

  return (
    <ModelCenter
      isLoading={isFetching}
      list={todoList}
      dateField={dateField}
      contentField={contentField}
      buttonText={`待处理任务 ${todoList.length}`}
      title="待处理任务"
      contentVerb="发起了"
      contentSuffix="的任务"
      onClick={onClick}
      {...restProps}
    />
  );

  function onClick(item: NotificationItem) {
    switch (item.type) {
      case NotificationType.TRUSTED_JOB_GROUP_CREATE:
        history.push(`/trusted-center/edit/${item.id}/receiver`);
        break;
      case NotificationType.TRUSTED_JOB_EXPORT:
        history.push(
          `/trusted-center/dataset-application/${item.id}/${item.coordinator_id}/${item.name}`,
        );
        break;
      default:
        break;
    }
  }
}
function ProjectNotice({
  dateField = 'created_at',
  contentField = 'name',
  ...restProps
}: TrainModelProps) {
  const history = useHistory();

  const { isFetching, data: todoPendingProjectList } = useQuery(
    ['fetchTodoPendingProjectList'],
    () =>
      fetchPendingProjectList({
        filter: filterExpressionGenerator(
          {
            state: [ProjectStateType.PENDING],
          },
          PENDING_PROJECT_FILTER_MAPPER,
        ),
        page: 1,
        page_size: 0,
      }),

    {
      refetchInterval: TIME_INTERVAL.LIST, // auto refresh every 1.5 min
      retry: 2,
      onError: (error) => {
        Message.error((error as Error).message);
      },
    },
  );

  const todoList = useMemo(() => {
    return todoPendingProjectList?.data ?? [];
  }, [todoPendingProjectList?.data]);

  return (
    <ModelCenter
      isLoading={isFetching}
      list={todoList}
      dateField={dateField}
      contentField={contentField}
      buttonText={`${todoList.length}条待处理工作区`}
      title="待处理工作区邀请"
      contentSuffix="的工作区邀请"
      onClick={onClick}
      {...restProps}
    />
  );

  function onClick(item: Project) {
    history.push(`/projects/receiver/${item.id}`);
  }
}

TodoPopover.ModelCenter = ModelCenter;
TodoPopover.NewTrainModel = NewTrainModel;
TodoPopover.EvaluationModelNew = EvaluationModelNew;
TodoPopover.AlgorithmManagement = AlgorithmManagement;
TodoPopover.ModelServing = ModelServingNotice;
TodoPopover.TrustedCenter = TrustedCenter;
TodoPopover.ProjectNotice = ProjectNotice;

export default TodoPopover;
