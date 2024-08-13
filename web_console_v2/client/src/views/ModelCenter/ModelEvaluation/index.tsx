import React from 'react';
import { Route, useRouteMatch, useParams, generatePath, Redirect } from 'react-router';
import List from './ModelEvaluationList';
import Detail from './ModelEvaluationDetail';
import routesMap, { ModelEvaluationListParams } from '../routes';

const ModelEvaluation: React.FC = () => {
  const matched = useRouteMatch();
  const params = useParams<ModelEvaluationListParams>();

  return (
    <>
      <Route exact path={routesMap.ModelEvaluationList} component={List} />
      <Route exact path={routesMap.ModelEvaluationDetail} component={Detail} />
      {matched.path === routesMap.ModelEvaluation && matched.isExact ? (
        <Redirect
          to={generatePath(routesMap.ModelEvaluationList, {
            module: params.module,
          })}
        />
      ) : null}
    </>
  );
};

export default ModelEvaluation;
