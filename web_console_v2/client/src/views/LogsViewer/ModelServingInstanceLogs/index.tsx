import React, { FC } from 'react';
import { useParams } from 'react-router-dom';

import { fetchModelServingInstanceLog_new } from 'services/modelServing';

import { useGetCurrentProjectId } from 'hooks';

import PrintLogs from 'components/PrintLogs';

const ModelServingInstanceLogs: FC = () => {
  const projectId = useGetCurrentProjectId();
  const params = useParams<{
    modelServingId: string;
    instanceName: string;
  }>();

  return (
    <PrintLogs
      logsFetcher={getLogs}
      refetchInterval={4000}
      queryKey={['getJob', params.modelServingId, params.instanceName]}
    />
  );

  async function getLogs(tailLines = 5000) {
    if (!params.modelServingId) {
      return { data: ['Model serving ID invalid!'] };
    }
    if (!params.instanceName) {
      return { data: ['Instance name invalid!'] };
    }
    if (!projectId) {
      return { data: ['请选择工作区！'] };
    }
    return fetchModelServingInstanceLog_new(
      projectId!,
      params.modelServingId,
      params.instanceName,
      {
        tail_lines: tailLines,
      },
    ).catch((error) => {
      return {
        data: [error.message],
      };
    });
  }
};

export default ModelServingInstanceLogs;
