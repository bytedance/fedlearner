import React, { FC } from 'react';
import { useQuery } from 'react-query';
import { Model } from 'typings/modelCenter';
import { fetchModelDetail_new } from 'services/modelCenter';
import { useGetCurrentProjectId } from 'hooks';
import { Spin, Space, Tag } from '@arco-design/web-react';
import CONSTANTS from 'shared/constants';

type Props = {
  id: ID;
  /** Fortmat display rext */
  formatter?: (model: Model) => string;
  isModelGroup?: Boolean;
};

function defaultFormatter(model: Model) {
  return model.name;
}

const WhichModel: FC<Props> = ({ id, formatter = defaultFormatter, isModelGroup = false }) => {
  const projectId = useGetCurrentProjectId();
  const modelQuery = useQuery(
    [`/v2/projects/${projectId}/models/${id}`],
    () => {
      return fetchModelDetail_new(projectId!, id).then((res) => res.data);
    },
    {
      enabled: Boolean(projectId) && (Boolean(id) || id === 0),
      retry: 2,
    },
  );

  if (modelQuery.isFetching) {
    return <Spin />;
  }

  return (
    <Space align="start">
      {modelQuery.data ? formatter(modelQuery.data) : CONSTANTS.EMPTY_PLACEHOLDER}
      {isModelGroup ? (
        <Tag size="small" color="blue">
          自动更新
        </Tag>
      ) : null}
    </Space>
  );
};

export default WhichModel;
