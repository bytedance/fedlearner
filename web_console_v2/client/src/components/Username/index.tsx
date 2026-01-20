/* istanbul ignore file */

import React, { FC } from 'react';
import { useRecoilQuery } from 'hooks/recoil';
import { userInfoQuery } from 'stores/user';
import { CONSTANTS } from 'shared/constants';

const Username: FC = () => {
  const query = useRecoilQuery(userInfoQuery);

  return <span>{query.data?.username || CONSTANTS.EMPTY_PLACEHOLDER}</span>;
};

export default Username;
