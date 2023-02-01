import React, { FC, useState } from 'react';
import { fetchDatasetJobStageById } from 'services/dataset';
import { useQuery } from 'react-query';
import { getIntersectionRate } from 'shared/dataset';
import { useGetCurrentProjectId } from 'hooks';
import { Message } from '@arco-design/web-react';

type Props = {
  datasetJobId: ID;
  datasetJobStageId: ID;
};
const DataBatchRate: FC<Props> = function ({ datasetJobId, datasetJobStageId }: Props) {
  const projectId = useGetCurrentProjectId();
  const [rate, setRate] = useState('-');
  const queryBatchState = useQuery(
    ['fetchDatasetJobStageById', projectId, datasetJobId, datasetJobStageId],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return;
      }
      return fetchDatasetJobStageById(projectId, datasetJobId, datasetJobStageId);
    },
    {
      retry: 2,
      enabled: Boolean(datasetJobId) && Boolean(datasetJobStageId),
      onSuccess(res) {
        if (!res) return;
        const { input_data_batch_num_example, output_data_batch_num_example } = res.data;
        setRate(
          getIntersectionRate({
            input: input_data_batch_num_example,
            output: output_data_batch_num_example,
          }),
        );
      },
    },
  );
  return <>{queryBatchState.isFetching ? '-' : rate}</>;
};

export default DataBatchRate;
