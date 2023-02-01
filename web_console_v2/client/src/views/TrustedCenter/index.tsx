import React, { FC } from 'react';
import { Redirect, Route, Switch, useLocation } from 'react-router-dom';
import ErrorBoundary from 'components/ErrorBoundary';
import TrustedJobList from './TrustedJobGroupList';
import CreateTrustedJobGroup from './CreateTrustedJobGroup';
import EditTrustedJobGroup from './EditTrustedJobGroup';
import TrustedJobGroupDetail from './TrustedJobGroupDetail';
import DatasetExportApplication from './DatasetExportApplication';
import ApplicationResult from './DatasetExportApplication/ApplicationResult';

const TrustedCenter: FC = () => {
  const location = useLocation();
  return (
    <ErrorBoundary>
      <Switch>
        <Route path="/trusted-center/list" exact component={TrustedJobList} />
        <Route
          path="/trusted-center/create/:role(receiver|sender)"
          component={CreateTrustedJobGroup}
        />
        <Route
          path="/trusted-center/edit/:id/:role(receiver|sender)"
          component={EditTrustedJobGroup}
        />
        <Route
          path="/trusted-center/detail/:id/:tabType(computing|export)"
          component={TrustedJobGroupDetail}
        />
        <Route
          path="/trusted-center/dataset-application/:result(passed|rejected)"
          component={ApplicationResult}
        />
        <Route
          path="/trusted-center/dataset-application/:id/:coordinator_id/:name"
          component={DatasetExportApplication}
        />
        {location.pathname === '/trusted-center' && <Redirect to="/trusted-center/list" />}
      </Switch>
    </ErrorBoundary>
  );
};

export default TrustedCenter;
