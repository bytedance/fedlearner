/* istanbul ignore file */
import React, { FC } from 'react';
import { useQuery } from 'react-query';

import { fetchParticipantDatasetList } from 'services/dataset';
import { useGetCurrentProjectId } from 'hooks';
import { CONSTANTS } from 'shared/constants';

import { Spin } from '@arco-design/web-react';
import { ParticipantDataset } from 'typings/dataset';

type UUIDProps = {
  uuid: string;
  loading?: boolean;
  /** It's useful to get participantDataset data */
  onAPISuccess?: (data?: ParticipantDataset) => void;
  emptyText?: React.ReactNode;
};

const WhichParticipantDataset: FC<UUIDProps> = ({
  uuid,
  loading,
  emptyText = CONSTANTS.EMPTY_PLACEHOLDER,
  onAPISuccess,
}) => {
  const projectId = useGetCurrentProjectId();

  const listQuery = useQuery(
    ['fetchParticipantDatasetList', 'WhichParticipantDataset', uuid, projectId],
    () =>
      fetchParticipantDatasetList(projectId!, {
        uuid,
      }),
    {
      enabled: Boolean(projectId) && Boolean(uuid),
      refetchOnWindowFocus: false,
      retry: 2,
      onSuccess(res) {
        onAPISuccess?.(res.data?.[0] ?? undefined);
      },
    },
  );

  if (loading || listQuery.isFetching) {
    return <Spin />;
  }

  return <span>{listQuery.data?.data?.[0]?.name ?? emptyText}</span>;
};

export default WhichParticipantDataset;
