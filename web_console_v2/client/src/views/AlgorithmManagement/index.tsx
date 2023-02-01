import ErrorBoundary from 'components/ErrorBoundary';
import React, { FC } from 'react';
import { Route, Redirect, useLocation, Switch } from 'react-router-dom';

import { AlgorithmManagementTabType } from 'typings/modelCenter';

import AlgorithmDetail from './AlgorithmDetail';
import AlgorithmForm from './AlgorithmForm';
import AlgorithmList from './AlgorithmList';

const AlgorithmManagement: FC = () => {
  const location = useLocation();

  return (
    <ErrorBoundary>
      <Switch>
        <Route
          path={`/algorithm-management/:tabType(${AlgorithmManagementTabType.MY}|${AlgorithmManagementTabType.BUILT_IN}|${AlgorithmManagementTabType.PARTICIPANT})`}
          exact
          component={AlgorithmList}
        />
        <Route path="/algorithm-management/:action(create|edit)" component={AlgorithmForm} />
        <Route
          path={`/algorithm-management/detail/:id/:tabType?/:algorithmDetailType?`}
          exact
          component={AlgorithmDetail}
        />
        {location.pathname === '/algorithm-management' && (
          <Redirect to={`/algorithm-management/${AlgorithmManagementTabType.MY}`} />
        )}
      </Switch>
    </ErrorBoundary>
  );
};

export default AlgorithmManagement;
