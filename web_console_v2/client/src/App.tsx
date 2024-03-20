import React, { ReactElement } from 'react';
import styled from 'styled-components';
import Header from 'components/Header';
import Sidebar from 'components/Sidebar';
import RouterViews from 'views';
import { Switch, Route } from 'react-router-dom';
import Login from 'views/Login';
import { useRecoilQuery } from 'hooks/recoil';
import { userInfoQuery } from 'stores/user';
import ProtectedRoute from 'views/ProtectedRoute';
import LogsViewer from 'views/LogsViewer';

const AppLayout = styled.div`
  display: grid;
  min-height: 100vh;
  max-height: 100vh;
  grid-template-areas:
    'header header'
    'sidebar main-content';
  grid-template-rows: auto 1fr;
  grid-template-columns: auto 1fr;
  overflow: hidden;
`;

const AppHeader = styled(Header)`
  grid-area: header;
  align-self: start;
`;

const AppSidebar = styled(Sidebar)`
  grid-area: sidebar;
`;

const AppMainContent = styled.main`
  position: relative;
  display: flex;
  flex-direction: column;
  grid-area: main-content;

  overflow: auto;
  overflow-anchor: auto;
`;

function App(): ReactElement {
  useRecoilQuery(userInfoQuery);

  return (
    <Switch>
      <Route exact path="/login" component={Login} />

      <ProtectedRoute path="/logs" component={LogsViewer} />

      <AppLayout>
        <AppHeader />
        <AppSidebar />
        <AppMainContent id="app-content">
          <RouterViews />
        </AppMainContent>
      </AppLayout>

      <Route path="*">You are lost</Route>
    </Switch>
  );
}

export default App;
