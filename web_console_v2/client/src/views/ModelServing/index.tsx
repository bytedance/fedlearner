import ErrorBoundary from 'components/ErrorBoundary';
import React, { FC } from 'react';
import { Route, Switch } from 'react-router-dom';

import ModelServingList from 'views/ModelServing/ModelServingList';
import ModelServingForm from 'views/ModelServing/ModelServingForm';
import ModelServingDetail from 'views/ModelServing/ModelServingDetail';

const ModelServing: FC = () => {
  return (
    <ErrorBoundary>
      <Switch>
        <Route path="/model-serving" exact component={ModelServingList} />
        <Route
          path="/model-serving/:action(create|edit)/:role(sender|receiver)?/:id?"
          exact
          component={ModelServingForm}
        />
        <Route path="/model-serving/detail/:id/:tabType?" exact component={ModelServingDetail} />
      </Switch>
    </ErrorBoundary>
  );
};

export default ModelServing;
