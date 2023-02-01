import { useResetRecoilState, useSetRecoilState } from 'recoil';
import {
  trainModelForm,
  evaluationModelForm,
  offlinePredictionModelForm,
} from 'stores/modelCenter';
import { treeTemplateIdQuery, nnTemplateIdQuery } from 'stores/modelCenter';
import { useRecoilQuery } from 'hooks/recoil';
import { useEffect, useMemo } from 'react';
import { useQueries, useQuery } from 'react-query';
import { useGetCurrentProjectId } from 'hooks';
import {
  fetchModelJobMetries_new,
  fetchPeerModelJobMetrics_new,
  fetchModelJob_new,
} from 'services/modelCenter';
import { ModelJob } from 'typings/modelCenter';
import { cloneDeep } from 'lodash-es';
import { getAlgorithmDetail } from 'services/algorithm';
import { EnumAlgorithmProjectType } from 'typings/algorithm';
import { Message } from '@arco-design/web-react';

export function useResetCreateForm() {
  const resetTrainModelForm = useResetRecoilState(trainModelForm);
  const resetEvaluationModelForm = useResetRecoilState(evaluationModelForm);
  const resetOfflinePredictionModelForm = useResetRecoilState(offlinePredictionModelForm);

  return function () {
    resetTrainModelForm();
    resetEvaluationModelForm();
    resetOfflinePredictionModelForm();
  };
}

export function useGetTrainModelTemplateId() {
  const { data: treeTemplateId, error: treeTemplateError } = useRecoilQuery(treeTemplateIdQuery);
  const { data: nnTemplateId, error: nnTemplateError } = useRecoilQuery(nnTemplateIdQuery);

  const setTreeTemplateId = useSetRecoilState(treeTemplateIdQuery);
  const setNNTemplateId = useSetRecoilState(nnTemplateIdQuery);

  useEffect(() => {
    if (treeTemplateId && !treeTemplateError) {
      setTreeTemplateId(treeTemplateId);
    }
  }, [treeTemplateId, treeTemplateError, setTreeTemplateId]);
  useEffect(() => {
    if (nnTemplateId && !nnTemplateError) {
      setNNTemplateId(nnTemplateId);
    }
  }, [nnTemplateId, nnTemplateError, setNNTemplateId]);

  return {
    treeTemplateId,
    nnTemplateId,
    treeTemplateError,
    nnTemplateError,
  };
}

export function useModelMetriesResult(jobId: ID, jobParticipantId?: ID) {
  const projectId = useGetCurrentProjectId();

  return useQuery(
    ['get_model_jobs_metries', jobId, projectId, jobParticipantId],
    () => {
      if (!jobParticipantId) {
        return fetchModelJobMetries_new(projectId!, jobId).then(
          (res: any) => res?.[0]?.data,
          (error) => {
            Message.error(error.message);
          },
        );
      } else if (jobParticipantId !== jobId) {
        return fetchPeerModelJobMetrics_new(projectId!, jobId, jobParticipantId!).then(
          (res) => res.data,
          (error) => {
            Message.error(error.message);
          },
        );
      } else {
        return Promise.resolve({});
      }
    },
    {
      enabled: Boolean(projectId),
    },
  );
}

export function useBatchModelJobMetricsAndConfig(jobList: ModelJob[], enable: boolean) {
  const projectId = useGetCurrentProjectId();
  const metricsQuery = useQueries(
    jobList.map((item) => ({
      enabled: Boolean(projectId && enable),
      queryKey: ['batch_model_job_metrics', item.id],
      queryFn() {
        return fetchModelJobMetries_new(projectId!, item.id).then((res: any) => res?.[0]?.data);
      },
    })),
  );
  const configQuery = useQueries(
    jobList.map((item) => ({
      enabled: Boolean(projectId && enable),
      queryKey: ['batch_model_job_config', item.id],
      async queryFn() {
        const variables = await fetchModelJob_new(projectId!, item.id).then(
          (res) => res.data.config.job_definitions?.[0].variables,
        );
        let parameterKeyList: string[] = [];

        if (
          item.algorithm_type === EnumAlgorithmProjectType.NN_VERTICAL ||
          item.algorithm_type === EnumAlgorithmProjectType.NN_HORIZONTAL
        ) {
          const algorithm = await getAlgorithmDetail(item.algorithm_id).then((res) => res.data);
          const parameters = algorithm.parameter?.variables ?? [];
          parameterKeyList = ['epoch_num', 'verbosity', ...parameters.map((p) => p.name)];
        } else if (item.algorithm_type === EnumAlgorithmProjectType.TREE_VERTICAL) {
          parameterKeyList = [
            'learning_rate',
            'max_iters',
            'max_depth',
            'l2_regularization',
            'max_bins',
            'num_parallel',
          ];
        }

        return variables.filter((v) => parameterKeyList.includes(v.name));
      },
    })),
  );

  return useMemo(() => {
    const ret = [];
    let isFetchedCount = 0;
    for (let i = 0; i < metricsQuery.length; i++) {
      const job = jobList[i];
      const mq = metricsQuery[i];
      const cq = configQuery[i];
      if (mq.isFetched || cq.isFetched) {
        isFetchedCount++;
        const mData = mq.data as any;
        const cData = cq.data as any;
        ret.push({
          id: job.name,
          job: job,
          config: cloneDeep(cData ?? []),
          metric: cloneDeep(mData ?? {}),
        });
      }
    }
    return {
      dataList: ret,
      isLoading: isFetchedCount < metricsQuery.length,
    };
  }, [metricsQuery, configQuery, jobList]);
}
