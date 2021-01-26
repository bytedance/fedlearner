import { useRecoilQuery } from 'hooks/recoil';
import React from 'react';
import { Redirect, Route, RouteProps, useLocation } from 'react-router-dom';
import { userInfoGetters } from 'stores/user';

interface Props extends RouteProps {
  isAuthenticated?: boolean;
}

function ProtectedRoute(props: Props) {
  const { isLoading, data } = useRecoilQuery(userInfoGetters);
  const location = useLocation();

  if (isLoading) {
    return <Route {...props} />;
  }

  if (!data || !data.isAuthenticated) {
    return <Redirect to={`/login?from=${encodeURIComponent(location.pathname)}`} />;
  }

  return <Route {...props} />;
}

export default ProtectedRoute;
