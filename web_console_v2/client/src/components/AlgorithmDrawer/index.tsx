/* istanbul ignore file */

import React, { FC, useState, useMemo } from 'react';
import { useQuery } from 'react-query';

import { fetchPeerAlgorithmProjectById, fetchProjectDetail } from 'services/algorithm';
import { CONSTANTS } from 'shared/constants';

import { Drawer, Spin, Button } from '@arco-design/web-react';
import AlgorithmInfo from './AlgorithmInfo';

import { Algorithm, AlgorithmParameter } from 'typings/algorithm';
import { DrawerProps } from '@arco-design/web-react/es/Drawer';
import { useGetCurrentProjectId } from 'hooks';

type Props = DrawerProps & {
  algorithmProjectId: ID;
  algorithmId?: ID;
  algorithmProjectUuid?: ID;
  algorithmUuid?: ID;
  participantId?: ID;
  parameterVariables?: AlgorithmParameter[];
  isAppendParameterVariables?: boolean;
};
type ButtonProps = Omit<Props, 'visible'> & {
  text?: string;
};

const AlgorithmDrawer: FC<Props> & {
  Button: FC<ButtonProps>;
} = ({
  algorithmProjectId,
  algorithmId,
  algorithmProjectUuid,
  algorithmUuid,
  participantId,
  parameterVariables,
  isAppendParameterVariables = false,
  ...resetProps
}) => {
  const projectId = useGetCurrentProjectId();
  const algorithmProjectDetailQuery = useQuery(
    ['getAlgorithmProjectDetailInAlgorithmDrawer', algorithmProjectId, algorithmId],
    () => fetchProjectDetail(algorithmProjectId),
    {
      // 对侧算法algorithmId为null
      //TODO:后端修改接口，对侧算法algorithm改为0，删除algorithmId为null的兼容逻辑
      enabled:
        (Boolean(algorithmProjectId) || algorithmProjectId === 0) &&
        algorithmId !== null &&
        algorithmId !== 0,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const peerAlgorithmProjectDetailQuery = useQuery(
    [
      'getFetchPeerAlgorithmProjectById',
      projectId,
      participantId,
      algorithmProjectUuid,
      algorithmId,
    ],
    () => fetchPeerAlgorithmProjectById(projectId, participantId, algorithmProjectUuid),
    {
      // 对侧算法algorithmId为null
      //TODO:后端修改接口，对侧算法algorithm改为0，删除algorithmId为null的兼容逻辑
      enabled:
        (algorithmId === null || algorithmId === 0) &&
        Boolean(algorithmProjectUuid) &&
        (Boolean(projectId) || projectId === 0) &&
        (Boolean(participantId) || participantId === 0),
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const algorithmProjectDetail = useMemo(() => {
    return algorithmId === null || algorithmId === 0
      ? peerAlgorithmProjectDetailQuery.data?.data
      : algorithmProjectDetailQuery.data?.data;
  }, [algorithmId, peerAlgorithmProjectDetailQuery, algorithmProjectDetailQuery]);

  const previewAlgorithm = useMemo<Algorithm | undefined>(() => {
    if (!algorithmProjectDetail) {
      return undefined;
    }

    const currentAlgorithm = algorithmProjectDetail.algorithms?.find(
      //旧模型训练可能没有algorithmUuid
      (item) => item.id === algorithmId || item.uuid === algorithmUuid,
    );

    if (!currentAlgorithm) return undefined;

    if (parameterVariables && parameterVariables.length > 0) {
      let finalVariables = parameterVariables;
      if (isAppendParameterVariables) {
        finalVariables = (currentAlgorithm?.parameter?.variables ?? []).concat(parameterVariables);
      }

      return {
        ...currentAlgorithm,
        parameter: {
          ...currentAlgorithm.parameter,
          variables: finalVariables,
        },
      };
    }

    return currentAlgorithm;
  }, [
    algorithmProjectDetail,
    algorithmId,
    algorithmUuid,
    parameterVariables,
    isAppendParameterVariables,
  ]);

  return (
    <Drawer
      closable
      width={1000}
      title={`算法 ${previewAlgorithm?.name ?? CONSTANTS.EMPTY_PLACEHOLDER} - 版本 V${
        previewAlgorithm?.version ?? CONSTANTS.EMPTY_PLACEHOLDER
      }`}
      {...resetProps}
    >
      <Spin
        loading={
          algorithmProjectDetailQuery.isFetching || peerAlgorithmProjectDetailQuery.isFetching
        }
        style={{ width: '100%' }}
      >
        <AlgorithmInfo
          type="algorithm"
          detail={previewAlgorithm}
          isParticipant={algorithmId === null || algorithmId === 0}
        />
      </Spin>
    </Drawer>
  );
};

export function _Button({ text = '查看', children, ...restProps }: ButtonProps) {
  const [visible, setVisible] = useState(false);
  return (
    <>
      {children ? (
        <span onClick={() => setVisible(true)}>{children}</span>
      ) : (
        <Button size="small" onClick={() => setVisible(true)} type="text">
          {text}
        </Button>
      )}
      <AlgorithmDrawer visible={visible} {...restProps} onCancel={() => setVisible(false)} />
    </>
  );
}

AlgorithmDrawer.Button = _Button;

export default AlgorithmDrawer;
