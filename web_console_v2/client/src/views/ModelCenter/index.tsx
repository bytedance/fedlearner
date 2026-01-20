import React from 'react';
import { Route, RouteProps } from 'react-router';

import ModelTrain from './ModelTrain';
import ModelWarehouse from './ModelWarehouse';
import ModelEvaluation from './ModelEvaluation';
import routesMap from './routes';

const routes: Array<RouteProps> = [
  {
    path: routesMap.ModelTrain,
    component: ModelTrain,
  },
  {
    path: routesMap.ModelWarehouse,
    component: ModelWarehouse,
  },
  {
    path: routesMap.ModelEvaluation,
    component: ModelEvaluation,
  },
];

const Index: React.FC = () => {
  return (
    <>
      {routes.map((r) => (
        <Route key={r.path as string} path={r.path} component={r.component} />
      ))}
    </>
  );
};

export default Index;
