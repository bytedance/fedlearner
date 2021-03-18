import { Spin } from 'antd';
import { useRecoilQuery } from 'hooks/recoil';
import React, { FC } from 'react';
import { projectListQuery } from 'stores/project';

const WhichProject: FC<{ id?: number | number; loading?: boolean }> = ({ id, loading }) => {
  const { isLoading, data } = useRecoilQuery(projectListQuery);

  if (loading || isLoading) {
    return <Spin size="small" />;
  }

  const project = data?.find((pj) => pj.id === Number(id)) || { name: 'none' };

  return <span>{project.name}</span>;
};

export default WhichProject;
