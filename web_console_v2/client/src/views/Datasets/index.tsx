import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import React, { FC } from 'react';
import { Route } from 'react-router-dom';
import CreateDataset from './CreateDataset';
import DatasetList from './DatasetList';

const DatasetsPage: FC = () => {
  return (
    <ErrorBoundary>
      <Route path="/datasets" component={DatasetList} />
      <Route path="/datasets/create" exact component={CreateDataset} />
    </ErrorBoundary>
  );
};

export default DatasetsPage;
