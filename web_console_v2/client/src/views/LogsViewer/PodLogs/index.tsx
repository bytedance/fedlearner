import React, { FC } from 'react';
import { useParams } from 'react-router-dom';
import { fetchPodLogs } from 'services/workflow';
import PrintLogs from 'components/PrintLogs';

const PodLogs: FC = () => {
  const params = useParams<{ jobId: string; podname: string }>();

  return (
    <PrintLogs
      logsFetcher={getLogs}
      refetchInterval={4000}
      queryKey={['getPodLogs', params.podname]}
    />
  );

  async function getLogs() {
    if (!params.podname || !params.jobId) {
      return { data: ['Pod name or Job ID invalid!'] };
    }

    return fetchPodLogs(params.podname, params.jobId, { maxLines: 900 }).catch((error) => ({
      data: error.message,
    }));
  }
};

export default PodLogs;
