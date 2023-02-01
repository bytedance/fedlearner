import ErrorBoundary from 'components/ErrorBoundary';
import React, { FC } from 'react';
import { Route } from 'react-router-dom';
import WorkflowDetail from 'views/Workflows/WorkflowDetail';
import DatasetDetail from './DatasetDetail';
import DatasetList from './DatasetList';
import DataSourceList from './DataSourceList';
import DataSourceDetail from './DataSourceDetail';
import TaskList from './TaskList';
import DatasetJobDetail from './DatasetJobDetail';
import NewDatasetJobDetail from './NewDatasetJobDetail';

const DatasetsPage: FC = () => {
  return (
    <ErrorBoundary>
      <Route path="/datasets/data_source" exact component={DataSourceList} />
      <Route path="/datasets/data_source/:id/:subtab?" exact component={DataSourceDetail} />
      <Route
        path="/datasets/:kind_label(raw|processed)/:tab(my|participant)?"
        exact
        render={(props) => {
          return <DatasetList {...props} key={(props?.match?.params as any)['kind_label']!} />; // force refresh when change kind_label
        }}
      />
      <Route
        path="/datasets/:kind_label(raw|processed)/detail/:id/:subtab?"
        exact
        render={(props) => {
          return <DatasetDetail {...props} key={(props?.match?.params as any)['kind_label']!} />; // force refresh when change kind_label
        }}
      />
      <Route path="/datasets/task_list" exact component={TaskList} />
      <Route
        path="/datasets/:kind_label(processed)/workflows/:id"
        exact
        component={WorkflowDetail}
      />
      <Route path="/datasets/job_detail/:job_id" exact component={DatasetJobDetail} />
      <Route
        path="/datasets/:dataset_id/new/job_detail/:job_id/:subtab?"
        exact
        component={NewDatasetJobDetail}
      />
    </ErrorBoundary>
  );
};

export default DatasetsPage;
