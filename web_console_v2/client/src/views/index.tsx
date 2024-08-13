import React, { FC, CSSProperties, Suspense } from 'react';
import routes, { noSidebarRoutes } from './routes';
import { Spin } from '@arco-design/web-react';
import { Switch, Route } from 'react-router-dom';
import ProtectedRoute from './ProtectedRoute';

import styled from 'styled-components';
import Header from 'components/Header';
import Sidebar from 'components/Sidebar';

import { appGetters } from 'stores/app';
import { useRecoilValue } from 'recoil';
import { convertToUnit } from 'shared/helpers';
import styles from './index.module.less';

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
  height: 100%;
`;

const BaseLayout: FC<{}> = ({ children }) => {
  const preferenceGetters = useRecoilValue(appGetters);

  return (
    <AppLayout
      style={{ '--SidebarWidth': convertToUnit(preferenceGetters.sidebarWidth) } as CSSProperties}
    >
      <AppHeader />
      <AppSidebar />
      <AppMainContent id="app-content">{children}</AppMainContent>
    </AppLayout>
  );
};
const NoSidebarLayout: FC<{}> = ({ children }) => {
  return (
    <AppLayout style={{ '--SidebarWidth': 0 } as CSSProperties}>
      <AppHeader />
      <AppMainContent id="app-content">{children}</AppMainContent>
    </AppLayout>
  );
};

function RouterViews() {
  if (!routes) {
    return null;
  }

  return (
    <Switch>
      {noSidebarRoutes.map((route, index) => {
        const { component: Component } = route;
        const RouteComponent = route.auth ? ProtectedRoute : Route;

        return (
          <RouteComponent
            key={index}
            path={route.path}
            exact={route.exact}
            render={(props: any) => (
              <NoSidebarLayout>
                <Component {...props} />
              </NoSidebarLayout>
            )}
            roles={route.roles}
            flagKeys={route.flagKeys}
            abilitiesSupport={route.abilitiesSupport}
          />
        );
      })}
      {routes.map((route, index) => {
        const { component: Component, async } = route;
        const RouteComponent = route.auth ? ProtectedRoute : Route;
        let AsyncComponent: any;
        if (async) {
          AsyncComponent = React.lazy(Component as any);
        }
        return (
          <RouteComponent
            key={index}
            path={route.path}
            exact={route.exact}
            render={(props: any) => (
              <BaseLayout>
                {async ? (
                  <Suspense fallback={<Spin loading={true} className={styles.route_spin} />}>
                    <AsyncComponent {...props} />
                  </Suspense>
                ) : (
                  <Component {...props} />
                )}
              </BaseLayout>
            )}
            roles={route.roles}
            flagKeys={route.flagKeys}
            abilitiesSupport={route.abilitiesSupport}
          />
        );
      })}
    </Switch>
  );
}

export default RouterViews;
