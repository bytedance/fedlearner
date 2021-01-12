import React, { ReactElement } from 'react';
import styled from 'styled-components';
import Header from 'components/Header';
import Sidebar from 'components/Sidebar';
import RouterViews from 'views';
import { Switch, Route } from 'react-router-dom';
import Login from 'views/Login';

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
  grid-area: main-content;
  padding: 16px;
  overflow: auto;
`;

function App(): ReactElement {
  return (
    <Switch>
      <Route exact path="/login" component={Login} />

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
