import React, { FC, useEffect, useMemo } from 'react';
import { useSetRecoilState } from 'recoil';

import { useCheckConnection } from 'hooks/participant';
import { participantConnectionState } from 'stores/participant';
import { TIME_INTERVAL } from 'shared/constants';

import GridRow from 'components/_base/GridRow';
import StateIndicator from 'components/StateIndicator';

import { ConnectionStatusType } from 'typings/participant';

export interface Props {
  id: ID;
  isNeedTip?: boolean;
  isNeedReCheck?: boolean;
}

export const globalParticipantIdToConnectionStateMap: {
  [key: number]: ConnectionStatusType;
} = {};

const PaticipantConnectionStatus: FC<Props> = ({
  id,
  isNeedTip = false,
  isNeedReCheck = false,
}) => {
  const setConnectionStatus = useSetRecoilState(participantConnectionState(id));

  const [checkStatus, reCheck] = useCheckConnection(id, {
    refetchOnWindowFocus: false,
    refetchInterval: TIME_INTERVAL.CONNECTION_CHECK,
  });

  const tipProps = useMemo(() => {
    if (isNeedTip) {
      return checkStatus.success === ConnectionStatusType.Fail ? { tip: checkStatus.message } : {};
    }
    return false;
  }, [checkStatus.message, checkStatus.success, isNeedTip]);

  useEffect(() => {
    // Store all connection state to sort table col data
    globalParticipantIdToConnectionStateMap[Number(id)] = checkStatus.success;
    setConnectionStatus(checkStatus);
  }, [id, checkStatus, setConnectionStatus]);

  return (
    <GridRow align="center" gap={5}>
      <StateIndicator
        type={checkStatus.success}
        text={getTextByType(checkStatus.success)}
        {...tipProps}
        afterText={
          isNeedReCheck &&
          checkStatus.success === ConnectionStatusType.Fail && (
            <button
              type="button"
              className="custom-text-button"
              onClick={() => reCheck(id)}
              style={{ marginLeft: 10 }}
            >
              重试
            </button>
          )
        }
      />
    </GridRow>
  );
  function getTextByType(type: ConnectionStatusType) {
    switch (type) {
      case ConnectionStatusType.Success:
        return '连接成功';
      case ConnectionStatusType.Processing:
        return '连接中';
      case ConnectionStatusType.Fail:
        return '连接失败';
    }
  }
};

export default PaticipantConnectionStatus;
