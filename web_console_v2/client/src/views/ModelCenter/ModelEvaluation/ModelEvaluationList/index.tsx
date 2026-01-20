import React, { FC, useMemo } from 'react';
import { debounce } from 'lodash-es';
import { useQuery } from 'react-query';
import { generatePath, useHistory, useParams } from 'react-router';
import { Button, Input, Message } from '@arco-design/web-react';
import SharedPageLayout from 'components/SharedPageLayout';
import GridRow from 'components/_base/GridRow';
import TodoPopover from 'components/TodoPopover';
import { useGetCurrentProjectId, useTablePaginationWithUrlState, useUrlState } from 'hooks';
import * as service from 'services/modelCenter';
import { ModelJob, ModelJobQueryParams_new as ModelJobQueryParams } from 'typings/modelCenter';
import { TIME_INTERVAL } from 'shared/constants';

import routesMap, { ModelEvaluationListParams } from '../../routes';
import EvaluationTable from '../ListTable';
import {
  dangerConfirmWrapper,
  deleteEvaluationJob,
  FILTER_MODEL_JOB_OPERATOR_MAPPER,
} from '../../shared';
import { IconPlus } from '@arco-design/web-react/icon';
import { filterExpressionGenerator } from 'views/Datasets/shared';
import { expression2Filter } from 'shared/filter';

type TProps = {};
const { Search } = Input;
const List: FC<TProps> = function () {
  const history = useHistory();
  const params = useParams<ModelEvaluationListParams>();
  const [urlState, setUrlState] = useUrlState<ModelJobQueryParams>({
    filter: filterExpressionGenerator(
      { auth_status: ['AUTHORIZED'] },
      FILTER_MODEL_JOB_OPERATOR_MAPPER,
    ),
  });
  const { urlState: pageInfo, paginationProps } = useTablePaginationWithUrlState();
  const projectId = useGetCurrentProjectId();
  const isModelEvaluation = params.module === 'model-evaluation';
  const listQuery = useQuery(
    [urlState.keyword, pageInfo.page, pageInfo.pageSize, projectId, params.module, urlState.filter],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return;
      }
      return service.fetchModelJobList_new(projectId, {
        page: pageInfo.page,
        page_size: pageInfo.pageSize,
        types: params.module === 'offline-prediction' ? 'PREDICTION' : 'EVALUATION',
        filter: urlState.filter || undefined,
      });
    },
    {
      enabled: Boolean(projectId),
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST,
      keepPreviousData: true,
      refetchOnWindowFocus: false,
      onError(err: any) {
        Message.error(err.message || err);
      },
    },
  );
  const { isFetching, data } = listQuery;
  const pagination = useMemo(() => {
    return (data?.page_meta?.total_items || 0) <= paginationProps.pageSize
      ? false
      : { ...paginationProps, total: data?.page_meta?.total_items };
  }, [data?.page_meta?.total_items, paginationProps]);
  return (
    <SharedPageLayout
      title={isModelEvaluation ? '模型评估' : '离线预测'}
      rightTitle={<TodoPopover.EvaluationModelNew module={params.module} />}
      key={params.module}
    >
      <GridRow justify="space-between" align="center">
        <Button
          type="primary"
          className={'custom-operation-button'}
          onClick={goToCreatePage}
          icon={<IconPlus />}
        >
          {params.module === 'model-evaluation' ? '创建评估' : '创建预测'}
        </Button>

        <Search
          className={'custom-input'}
          allowClear
          placeholder={isModelEvaluation ? '输入评估任务名称' : '输入预测任务名称'}
          defaultValue={urlState.keyword}
          onChange={debounce((keyword) => {
            const filter = expression2Filter(urlState.filter);
            setUrlState((preState) => ({
              ...preState,
              page: 1,
              keyword,
              filter: filterExpressionGenerator(
                { ...filter, name: keyword, auth_status: ['AUTHORIZED'] },
                FILTER_MODEL_JOB_OPERATOR_MAPPER,
              ),
            }));
          }, 300)}
        />
      </GridRow>
      <EvaluationTable
        className="custom-table custom-table-left-side-filter"
        data={data?.data}
        loading={isFetching}
        module={params.module}
        pagination={pagination}
        filterDropdownValues={{
          algorithm_type: expression2Filter(urlState.filter).algorithm_type,
          status: expression2Filter(urlState.filter).status,
          role: expression2Filter(urlState.filter).role,
        }}
        nameFieldText={!isModelEvaluation ? '预测任务名称' : '评估任务名称'}
        onChange={(_, sorter, filters, extra) => {
          if (extra.action === 'filter') {
            setUrlState((preState) => ({
              ...preState,
              filter: filterExpressionGenerator(
                {
                  algorithm_type: filters.algorithm_type,
                  status: filters.status,
                  role: filters.role,
                  name: urlState.keyword,
                  auth_status: ['AUTHORIZED'],
                },
                FILTER_MODEL_JOB_OPERATOR_MAPPER,
              ),
              page: 1,
            }));
          }
        }}
        onStopClick={(job: ModelJob) => {
          return stopJob(job);
        }}
        onDeleteClick={(job: ModelJob) => {
          return deleteJob(job);
        }}
      />
    </SharedPageLayout>
  );

  function goToCreatePage() {
    history.push(
      generatePath(routesMap.ModelEvaluationCreate, {
        module: params.module,
        role: 'sender',
        action: 'create',
      }),
    );
  }

  async function stopJob(job: ModelJob) {
    if (!projectId) {
      throw new Error('请选择工作区');
    }

    dangerConfirmWrapper(
      `确认要终止「${job.name}」？`,
      '终止后，该评估任务将无法重新运行，请谨慎操作',
      '终止',
      async () => {
        try {
          await service.stopJob_new(projectId!, job.id);
          Message.success('停止成功');
          listQuery.refetch();
        } catch (e) {
          Message.error(e.message);
        }
      },
    );
  }

  async function deleteJob(job: ModelJob) {
    if (!projectId) {
      throw new Error('请选择工作区');
    }
    try {
      await deleteEvaluationJob(projectId, job, params.module);
      listQuery.refetch();
    } catch (error: any) {}
  }
};

export default List;
