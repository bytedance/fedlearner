import { userInfoQuery, userInfoGetters } from 'stores/user';
import { useRecoilQuery } from 'hooks/recoil';
import { FedRoles } from 'typings/auth';

export function useGetUserInfo() {
  const { data } = useRecoilQuery(userInfoQuery);
  // TODO: maybe undefined
  return data;
}

export function useIsAdminRole() {
  const { isLoading, data } = useRecoilQuery(userInfoGetters);

  return !isLoading && data && data.role === FedRoles.Admin;
}
