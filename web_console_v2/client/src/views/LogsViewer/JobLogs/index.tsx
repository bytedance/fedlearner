import React, { FC } from 'react';
import { useParams } from 'react-router-dom';
import { fetchJobLogs } from 'services/workflow';
import PrintLogs from 'components/PrintLogs';

const PodLogs: FC = () => {
  const params = useParams<{ jobname: string }>();

  return <PrintLogs logsFetcher={getLogs} queryKey={['getJob', params.jobname]} />;

  async function getLogs() {
    if (!params.jobname) {
      return { data: ['Job name invalid!'] };
    }

    return fetchJobLogs(params.jobname, {
      startTime: 0,
      maxLines: 500,
    }).catch((error) => ({
      data: [error.message],
    }));
  }
};

export default PodLogs;
