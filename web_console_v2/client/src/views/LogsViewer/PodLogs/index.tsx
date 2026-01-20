import React, { FC } from 'react';
import { useParams } from 'react-router-dom';
import { fetchPodLogs } from 'services/workflow';
import PrintLogs from 'components/PrintLogs';

const PodLogs: FC = () => {
  const params = useParams<{ jobId: string; podname: string; startTime?: string }>();

  return (
    <PrintLogs
      logsFetcher={getLogs}
      refetchInterval={4000}
      queryKey={['getPodLogs', params.podname]}
    />
  );

  async function getLogs(maxLines = 900) {
    if (!params.podname || !params.jobId) {
      return { data: ['Pod name or Job ID invalid!'] };
    }

    return fetchPodLogs(params.podname, params.jobId, {
      maxLines,
      startTime: params.startTime !== undefined ? 0 : undefined,
    }).catch((error) => {
      return { data: [error.message] };
    });
  }
};

export default PodLogs;
