import React, { FC } from 'react';
import { useParams } from 'react-router-dom';
import { fetchJobLogs } from 'services/workflow';
import PrintLogs from 'components/PrintLogs';

const PodLogs: FC = () => {
  const params = useParams<{ jobId: string }>();

  return (
    <PrintLogs logsFetcher={getLogs} refetchInterval={4000} queryKey={['getJob', params.jobId]} />
  );

  async function getLogs() {
    if (!params.jobId) {
      return { data: ['Job ID invalid!'] };
    }

    return fetchJobLogs(params.jobId, {
      maxLines: 500,
    }).catch((error) => ({
      data: [error.message],
    }));
  }
};

export default PodLogs;
