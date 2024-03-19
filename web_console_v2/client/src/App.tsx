import React, { ReactElement } from 'react';
import RouterViews from 'views';
import { Switch, Route } from 'react-router-dom';
import Login from 'views/Login';
import SSOCallback from 'views/SSOCallback';
import TokenCallback from 'views/TokenCallback';
import { useRecoilQuery } from 'hooks/recoil';
import { userInfoQuery } from 'stores/user';
import { appFlag } from 'stores/app';
import ProtectedRoute from 'views/ProtectedRoute';
import LogsViewer from 'views/LogsViewer';
import { useSetRecoilState } from 'recoil';
import { useQuery } from 'react-query';
import { fetchFlagList } from 'services/flag';
import { TIME_INTERVAL } from 'shared/constants';

function App(): ReactElement {
  useRecoilQuery(userInfoQuery);
  const setAppFlag = useSetRecoilState(appFlag);

  // Fetch flag list every 10 min
  useQuery(['fetchFlagList'], () => fetchFlagList(), {
    retry: 2,
    refetchOnWindowFocus: false,
    refetchInterval: TIME_INTERVAL.FLAG,
    onSuccess(data) {
      // Save to recoil and it will store localstorage too
      setAppFlag(data.data ?? {});
    },
  });

  return (
    <Switch>
      {/*
       * /sso-callback/:ssoName only be opened by other login way in views/Login/index.tsx,
       *
       * it support standard protocol, including OAuth, CAS, etc.
       *
       */}
      <Route exact path="/sso-callback/:ssoName" component={SSOCallback} />
      {/*
       * /token-callback will get access_token from url query,
       * and then get userInfo by this access_token.
       *
       * If get userInfo successfully, jump page to /projects
       *
       * it support SPD Bank
       *
       */}
      <Route exact path="/token-callback" component={TokenCallback} />
      <Route exact path="/login" component={Login} />
      <ProtectedRoute path="/logs" component={LogsViewer} />
      <RouterViews />
      <Route path="*">You are lost</Route>
    </Switch>
  );
}

export default App;
