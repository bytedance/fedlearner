import { useMemo } from 'react';
import { useSetRecoilState } from 'recoil';
import { useQuery, UseQueryOptions } from 'react-query';
import { checkParticipantConnection } from 'services/participant';
import { ConnectionStatus, ConnectionStatusType, Version } from 'typings/participant';
import { forceReloadParticipantList } from 'stores/participant';

export function useReloadParticipantList() {
  const setter = useSetRecoilState(forceReloadParticipantList);

  return function () {
    setter(Math.random());
  };
}

export function useCheckConnection(
  partnerId: ID,
  options?: UseQueryOptions<{
    data: { success: boolean; message: string; application_version: Version };
  }>,
): [ConnectionStatus, Function] {
  const checkQuery = useQuery(
    [`checkConnection-participant-${partnerId}`, partnerId],
    () => checkParticipantConnection(partnerId),
    {
      enabled: Boolean(partnerId),
      cacheTime: 1,
      retry: false,
      ...options,
    },
  );

  const finalStatus = useMemo(() => {
    const status = {
      success: ConnectionStatusType.Processing,
      message: '',
      application_version: {},
    };
    if (!checkQuery.isFetching) {
      if (checkQuery.isError) {
        status.success = ConnectionStatusType.Fail;
        status.message = (checkQuery.error as Error).message;
      } else {
        const queryData = checkQuery.data?.data;
        if (queryData) {
          status.message = queryData.message;
          status.application_version = queryData.application_version;
          status.success = queryData.success
            ? ConnectionStatusType.Success
            : ConnectionStatusType.Fail;
        }
      }
    }
    return status;
  }, [checkQuery]);

  return [finalStatus, checkQuery.refetch];
}
