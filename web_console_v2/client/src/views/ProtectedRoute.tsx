import { useRecoilQuery } from 'hooks/recoil';
import React from 'react';
import { Redirect, Route, RouteProps, useLocation } from 'react-router-dom';
import { userInfoGetters } from 'stores/user';
import { FedRoles } from 'typings/auth';

interface Props extends RouteProps {
  isAuthenticated?: boolean;
  roles?: FedRoles[];
}

function isMatchRoute(userRole: FedRoles, routeRoles: FedRoles[]) {
  return routeRoles.indexOf(userRole) !== -1;
}

function ProtectedRoute(props: Props) {
  const { isLoading, data } = useRecoilQuery(userInfoGetters);
  const location = useLocation();
  const { roles: routeRoles } = props;

  if (isLoading) {
    return <Route {...props} />;
  }

  if (!data || !data.isAuthenticated) {
    return <Redirect to={`/login?from=${encodeURIComponent(location.pathname)}`} />;
  }

  if (routeRoles && !isMatchRoute(data.role, routeRoles)) {
    return <Redirect to="/" />;
  }

  return <Route {...props} />;
}

export default ProtectedRoute;
