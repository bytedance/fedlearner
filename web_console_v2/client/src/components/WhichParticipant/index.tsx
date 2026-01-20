/* istanbul ignore file */
import React, { FC } from 'react';

import { useRecoilQuery } from 'hooks/recoil';
import { participantListQuery } from 'stores/participant';
import { CONSTANTS } from 'shared/constants';

import { Spin } from '@arco-design/web-react';

type Props = {
  id?: ID;
  loading?: boolean;
};

const WhichParticipant: FC<Props> = ({ id, loading }) => {
  const { isLoading, data } = useRecoilQuery(participantListQuery);

  if (loading || isLoading) {
    return <Spin />;
  }

  const participant = data?.find((item) => Number(item.id) === Number(id)) || {
    name: CONSTANTS.EMPTY_PLACEHOLDER,
  };

  return <span>{participant.name}</span>;
};

export default WhichParticipant;
