import { useQuery, UseQueryOptions } from 'react-query';
import { useResetRecoilState, useSetRecoilState } from 'recoil';
import { checkConnection } from 'services/project';
import { forceReloadProjectList, projectCreateForm, projectJoinForm } from 'stores/project';
import { ConnectionStatus, Project } from 'typings/project';

export function useCheckConnection(
  project: Project,
  options?: UseQueryOptions<{ data: { success: boolean } }>,
): [ConnectionStatus, Function] {
  const checkQuery = useQuery(
    [`checkConnection-project-${project.id}`, project.id],
    () => checkConnection(project.id),
    {
      cacheTime: 1,
      retry: false,
      ...options,
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

export function useResetCreateForm() {
  const resetCreateForm = useResetRecoilState(projectCreateForm);

  return function () {
    resetCreateForm();
  };
}
export function useResetJoinForm() {
  const resetJoinForm = useResetRecoilState(projectJoinForm);

  return function () {
    resetJoinForm();
  };
}
