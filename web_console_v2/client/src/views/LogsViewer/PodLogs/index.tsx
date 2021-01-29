import { Refresh } from 'components/IconPark';
import React, { FC } from 'react';
import { useQuery } from 'react-query';
import { useParams } from 'react-router-dom';
import { fetchPodLogs } from 'services/workflow';
import styled from 'styled-components';

const Container = styled.div``;

const PodLogs: FC = () => {
  const params = useParams<{ jobid: string; podname: string }>();

  const logsQuery = useQuery('getPodLogs', getLogs, {
    refetchOnWindowFocus: false,
  });

  if (logsQuery.isFetching) {
    return <Refresh className="anticon-spin" style={{ fontSize: '20px' }} />;
  }

  return <Container>{logsQuery.data?.data}</Container>;

  async function getLogs() {
    if (!params.jobid || !params.podname) {
      return { data: 'Job ID or Pod name invalid!' };
    }

    return fetchPodLogs(params.jobid, params.podname).catch((error) => ({ data: error.message }));
  }
};

export default PodLogs;
