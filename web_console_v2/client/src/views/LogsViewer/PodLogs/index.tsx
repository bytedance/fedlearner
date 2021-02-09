import React, { FC } from 'react';
import { useParams } from 'react-router-dom';
import { fetchPodLogs } from 'services/workflow';
import PrintLogs from 'components/PrintLogs';

const PodLogs: FC = () => {
  const params = useParams<{ jobid: string; podname: string }>();

  return <PrintLogs logsFetcher={getLogs} queryKey={['getPodLogs', params.podname]} />;

  async function getLogs() {
    if (!params.podname) {
      return { data: ['Pod name invalid!'] };
    }

    return fetchPodLogs(params.podname, { startTime: 0, maxLines: 900 }).catch((error) => ({
      data: error.message,
    }));
  }
};

export default PodLogs;
