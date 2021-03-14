import React, { FC } from 'react';
import { useParams } from 'react-router-dom';
import { fetchJobEvents, fetchPeerJobEvents } from 'services/workflow';
import PrintLogs from 'components/PrintLogs';

const PodLogs: FC = () => {
  const params = useParams<{ side: string; jobIdOrName: string; uuid?: string }>();

  const isPeerSide = params.side === 'peer';

  return (
    <PrintLogs
      logsFetcher={getLogs}
      refetchInterval={4000}
      queryKey={['getJobEvents', params.jobIdOrName]}
    />
  );

  async function getLogs() {
    if (!params.jobIdOrName) {
      return { data: ['Job ID or Name invalid!'] };
    }

    if (isPeerSide) {
      return fetchPeerJobEvents(params.uuid!, params.jobIdOrName, {
        maxLines: 500,
      }).catch((error) => ({
        data: [error.message],
      }));
    }

    return fetchJobEvents(params.jobIdOrName, {
      maxLines: 500,
    }).catch((error) => ({
      data: [error.message],
    }));
  }
};

export default PodLogs;
