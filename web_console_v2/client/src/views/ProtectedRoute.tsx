import { useRecoilQuery } from 'hooks/recoil';
import React from 'react';
import { Redirect, Route, RouteProps, useLocation, useHistory } from 'react-router-dom';
import { userInfoGetters } from 'stores/user';
import { userInfoQuery, userInfoState } from 'stores/user';
import { appFlag } from 'stores/app';
import { Flag } from 'typings/flag';
import { FedRoles } from 'typings/auth';
import { useGetCurrentProjectAbilityConfig, useSubscribe } from 'hooks';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { useResetRecoilState, useRecoilValue } from 'recoil';
import { Message } from '@arco-design/web-react';
import { ProjectBaseAbilitiesType, ProjectTaskType } from 'typings/project';

interface Props extends RouteProps {
  isAuthenticated?: boolean;
  roles?: FedRoles[];
  flagKeys?: string[];
  abilitiesSupport?: (ProjectTaskType | ProjectBaseAbilitiesType)[];
}

function isMatchRole(userRole: FedRoles, routeRoles: FedRoles[]) {
  return routeRoles.indexOf(userRole) !== -1;
}

function isMatchFlag(flagValue: Flag, flagKeys: string[]) {
  if (
    flagKeys.some((flag) => {
      if (Object.prototype.hasOwnProperty.call(flagValue, flag) && !flagValue[flag]) {
        return true;
      }

      return false;
    })
  ) {
    return false;
  }

  return true;
}

function isMatchAbilities(
  abilities: (ProjectTaskType | ProjectBaseAbilitiesType)[] | undefined,
  abilitiesSupport: (ProjectTaskType | ProjectBaseAbilitiesType)[],
) {
  if (!abilities?.[0]) {
    return true;
  }
  return abilitiesSupport.includes(abilities?.[0]);
}

function ProtectedRoute(props: Props) {
  const { isLoading, data } = useRecoilQuery(userInfoGetters);
  const { abilities } = useGetCurrentProjectAbilityConfig();
  const resetUserInfoState = useResetRecoilState(userInfoState);
  const resetUserInfo = useResetRecoilState(userInfoQuery);
  const appFlagValue = useRecoilValue(appFlag);
  const history = useHistory();

  const location = useLocation();
  const { roles: routeRoles, flagKeys, abilitiesSupport } = props;

  // If API return 422/401 status code, then go to login page
  useSubscribe('logout', logout);

  if (isLoading) {
    return null;
  }

  if (!data || !data.isAuthenticated) {
    return (
      <Redirect to={`/login?from=${encodeURIComponent(location.pathname + location.search)}`} />
    );
  }

  // FlagKey
  if (flagKeys && !isMatchFlag(appFlagValue, flagKeys)) {
    return <Redirect to="/" />;
  }

  // Role
  if (routeRoles && !isMatchRole(data.role, routeRoles)) {
    return <Redirect to="/" />;
  }

  // project abilities
  if (abilitiesSupport && !isMatchAbilities(abilities, abilitiesSupport)) {
    return <Redirect to="/" />;
  }

  return <Route {...props} />;

  function logout(_: any, data: any) {
    // clear local state
    store.remove(LOCAL_STORAGE_KEYS.current_user);
    store.remove(LOCAL_STORAGE_KEYS.sso_info);
    resetUserInfoState();
    resetUserInfo();

    // show tips
    Message.info(data.message);

    // redirect
    history.push(`/login`);
  }
}

export default ProtectedRoute;
