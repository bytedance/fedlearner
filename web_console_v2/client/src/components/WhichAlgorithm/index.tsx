import React, { useMemo } from 'react';
import { useQuery } from 'react-query';
import { Spin } from '@arco-design/web-react';
import { fetchPeerAlgorithmDetail, getAlgorithmDetail } from 'services/algorithm';
import { Algorithm } from 'typings/algorithm';
import CONSTANTS from 'shared/constants';
import { useGetCurrentProjectId } from 'hooks';

type Props = {
  id: ID;
  /** Format display text */
  formatter?: (algorithm: Algorithm) => string;
  uuid?: ID;
  participantId?: ID;
};

function defaultFormatter(algorithm: Algorithm) {
  return `${algorithm.name} (V${algorithm.version})`;
}

const WhichAlgorithm: React.FC<Props> = ({
  id,
  uuid,
  formatter = defaultFormatter,
  participantId,
}) => {
  const projectId = useGetCurrentProjectId();
  const algorithmDetailQuery = useQuery(['getAlgorithmDetail', id], () => getAlgorithmDetail(id!), {
    enabled: (Boolean(id) || id === 0) && !Boolean(participantId),
    retry: 2,
  });
  const peerAlgorithmDetailQuery = useQuery(
    ['getPeerAlgorithmDetailQuery', projectId, participantId, uuid],
    () => fetchPeerAlgorithmDetail(projectId, participantId, uuid),
    {
      enabled:
        (id === null || participantId !== 0) &&
        Boolean(uuid) &&
        (Boolean(projectId) || projectId === 0) &&
        Boolean(participantId),
      retry: 2,
    },
  );
  const algorithmDetail = useMemo(() => {
    return id === null || participantId !== 0
      ? peerAlgorithmDetailQuery.data?.data
      : algorithmDetailQuery.data?.data;
  }, [peerAlgorithmDetailQuery, algorithmDetailQuery, id, participantId]);

  if (algorithmDetailQuery.isFetching || peerAlgorithmDetailQuery.isFetching) {
    return <Spin />;
  }

  return <span>{algorithmDetail ? formatter(algorithmDetail) : CONSTANTS.EMPTY_PLACEHOLDER}</span>;
};

export default WhichAlgorithm;
