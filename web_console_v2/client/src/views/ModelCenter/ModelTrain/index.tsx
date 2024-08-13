import React from 'react';
import { Route } from 'react-router';
import List from './List';
import Detail from './Detail';
import routesMap from '../routes';

const ModelTrain: React.FC = () => {
  return (
    <>
      <Route exact path={routesMap.ModelTrainList} component={List} />
      <Route exact path={routesMap.ModelTrainDetail} component={Detail} />
    </>
  );
};

export default ModelTrain;
