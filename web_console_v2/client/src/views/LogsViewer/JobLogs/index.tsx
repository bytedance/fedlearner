import React, { FC } from 'react';
import { useParams } from 'react-router-dom';
import { fetchJobLogs } from 'services/workflow';
import PrintLogs from 'components/PrintLogs';

const JobLogs: FC = () => {
  const params = useParams<{ jobId: string }>();

  return (
    <PrintLogs logsFetcher={getLogs} refetchInterval={4000} queryKey={['getJob', params.jobId]} />
  );

  async function getLogs(maxLines = 5000) {
    if (!params.jobId) {
      return { data: ['Job ID invalid!'] };
    }

    return fetchJobLogs(params.jobId, {
      maxLines,
    }).catch((error) => ({
      data: [error.message],
    }));
  }
};

export default JobLogs;
