/* istanbul ignore file */
import React, { FC } from 'react';

import { useRecoilQuery } from 'hooks/recoil';
import { projectListQuery } from 'stores/project';
import { CONSTANTS } from 'shared/constants';

import { Spin } from '@arco-design/web-react';

type Props = {
  id?: ID;
  loading?: boolean;
};

const WhichProject: FC<Props> = ({ id, loading }) => {
  const { isLoading, data } = useRecoilQuery(projectListQuery);

  if (loading || isLoading) {
    return <Spin />;
  }

  const project = data?.find((pj) => pj.id === Number(id)) || { name: CONSTANTS.EMPTY_PLACEHOLDER };

  return <span>{project.name}</span>;
};

export default WhichProject;
