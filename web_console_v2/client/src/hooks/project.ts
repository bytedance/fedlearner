import { useQuery } from 'react-query';
import { useSetRecoilState } from 'recoil';
import { checkConnection } from 'services/project';
import { forceReloadProjectList } from 'stores/project';
import { ConnectionStatus, Project } from 'typings/project';

export function useCheckConnection(project: Project): [ConnectionStatus, Function] {
  const checkQuery = useQuery(
    [`checkConnection-${project.id}`, project.id],
    () => checkConnection(project.id),
    {
      cacheTime: 1,
      retry: false,
    },
  );

  const successOrFailed = checkQuery.isError
    ? ConnectionStatus.CheckFailed
    : checkQuery.data?.data.success
    ? ConnectionStatus.Success
    : ConnectionStatus.Failed;

  const status = checkQuery.isFetching ? ConnectionStatus.Checking : successOrFailed;

  return [status, checkQuery.refetch];
}

export function useReloadProjectList() {
  const setter = useSetRecoilState(forceReloadProjectList);

  return function () {
    setter(Math.random());
  };
}
