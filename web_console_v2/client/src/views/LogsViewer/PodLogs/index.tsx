import { Refresh } from 'components/IconPark';
import React, { FC, useRef, useEffect } from 'react';
import { useQuery } from 'react-query';
import { useParams } from 'react-router-dom';
import { fetchPodLogs } from 'services/workflow';

const PodLogs: FC = () => {
  const panelRef = useRef<HTMLPreElement>();
  const params = useParams<{ jobid: string; podname: string }>();

  const logsQuery = useQuery('getPodLogs', getLogs, {
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (panelRef.current) {
      panelRef.current.parentElement?.parentElement?.scrollTo({
        top: panelRef.current.scrollHeight,
      });
    }
  }, [logsQuery.data]);

  if (logsQuery.isFetching) {
    return <Refresh spin style={{ fontSize: '20px' }} />;
  }

  const isEmpty = logsQuery.data?.data.length === 0;

  return (
    <div ref={panelRef as any}>
      {isEmpty ? 'Ooops! No logs at the moment' : logsQuery.data?.data.join('\n')}
    </div>
  );

  async function getLogs() {
    if (!params.podname) {
      return { data: 'Pod name invalid!' };
    }

    return fetchPodLogs(params.podname, { startTime: 0, maxLines: 500 }).catch((error) => ({
      data: error.message,
    }));
  }
};

export default PodLogs;
