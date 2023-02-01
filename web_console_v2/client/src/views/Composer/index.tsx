import React from 'react';
import { Redirect, Route, Switch, useLocation } from 'react-router-dom';
import SchedulerItemList from './SchedulerItemList';
import SchedulerItemDetail from './SchedulerItemDetail';
import SchedulerRunnerList from './SchedulerRunnerList';
import ErrorBoundary from 'components/ErrorBoundary';

function Composer() {
  const location = useLocation();
  return (
    <ErrorBoundary>
      <Switch>
        <Route path={'/composer/scheduler-item/list'} exact component={SchedulerItemList} />
        <Route path={'/composer/scheduler-runner/list'} exact component={SchedulerRunnerList} />
        <Route
          path={'/composer/scheduler-item/detail/:item_id'}
          exact
          component={SchedulerItemDetail}
        />
        {location.pathname === '/composer' && <Redirect to="/composer/scheduler-item/lis" />}
      </Switch>
    </ErrorBoundary>
  );
}

export default Composer;
