import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import React, { FC } from 'react';
import { Route } from 'react-router-dom';
import DatasetsTable from './DatasetsTable';

const DatasetsPage: FC = () => {
  return (
    <ErrorBoundary>
      <Route path="/datasets" exact component={DatasetsTable} />
    </ErrorBoundary>
  );
};

export default DatasetsPage;
