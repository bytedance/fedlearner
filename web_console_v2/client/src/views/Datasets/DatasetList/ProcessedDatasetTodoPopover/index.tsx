import React, { useMemo } from 'react';
import { Message } from '@arco-design/web-react';
import { useQuery } from 'react-query';
import { Dataset } from 'typings/dataset';
import { fetchDatasetList } from 'services/dataset';
import { useHistory } from 'react-router-dom';
import { useGetCurrentProjectId } from 'hooks';
import TodoPopover from 'components/TodoPopover';
import { TIME_INTERVAL } from 'shared/constants';
import { ApprovalProps } from 'components/TodoPopover';
import { FILTER_OPERATOR_MAPPER, filterExpressionGenerator } from '../../shared';
import { DatasetProcessedMyAuthStatus } from 'typings/dataset';

type ProcessedDatasetProps<T = any> = Omit<ApprovalProps<T>, 'list'> & {};

function ProcessedDatasetTodoPopover({
  dateField = 'created_at',
  creatorField = 'creator',
  contentField = 'name',
  ...restProps
}: ProcessedDatasetProps) {
  const history = useHistory();
  const projectId = useGetCurrentProjectId();

  const { isError, data, error, isFetching } = useQuery<{
    data: Array<Dataset>;
  }>(
    ['fetchDatasetList', projectId],
    () => {
      if (!projectId!) {
        Message.info('请选择工作区');
        return Promise.resolve({ data: [] });
      }
      return fetchDatasetList({
        filter: filterExpressionGenerator(
          {
            dataset_kind: 'PROCESSED',
            project_id: projectId,
            auth_status: [DatasetProcessedMyAuthStatus.PENDING],
          },
          FILTER_OPERATOR_MAPPER,
        ),
        order_by: 'created_at desc',
      });
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST,
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
    <TodoPopover.ModelCenter
      isLoading={isFetching}
      list={todoList}
      dateField={dateField}
      contentField={contentField}
      buttonText={`${todoList.length}条待处理结果数据集`}
      title="待处理数据集授权申请"
      contentVerb="发起了"
      contentSuffix="数据集授权申请"
      onClick={onClick}
      {...restProps}
    />
  );

  function onClick(item: Dataset) {
    history.push(`/datasets/processed/authorize/${item.id}`);
  }
}

export default ProcessedDatasetTodoPopover;
