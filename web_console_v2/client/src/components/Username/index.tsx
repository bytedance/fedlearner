import React, { FC } from 'react';
import { useRecoilQuery } from 'hooks/recoil';
import { userInfoQuery } from 'stores/user';

const Username: FC = () => {
  const query = useRecoilQuery(userInfoQuery);

  return <span>{query.data?.username || '-'}</span>;
};

export default Username;
