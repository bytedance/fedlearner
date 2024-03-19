import React, { FC } from 'react';

import { useRecoilQuery } from 'hooks/recoil';
import { participantListQuery } from 'stores/participant';
import { Spin } from '@arco-design/web-react';

type Props = {
  pureDomainName?: string;
  loading?: boolean;
  contentField: string;
};

const ParticipantDetail: FC<Props> = ({ pureDomainName, loading, contentField }) => {
  const { isLoading, data } = useRecoilQuery(participantListQuery);
  const participant = data?.find((item) => item.pure_domain_name === pureDomainName) as Record<
    string,
    any
  >;

  return (
    <Spin loading={isLoading || loading}>
      <span>{participant?.[contentField] ?? '-'}</span>;
    </Spin>
  );
};

export default ParticipantDetail;
