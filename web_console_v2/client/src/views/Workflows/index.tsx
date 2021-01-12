import React from 'react';

import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import { Route, Redirect } from 'react-router-dom';
import WorkflowsList from './WorkflowList';
import WorkflowsCreate from './CreateWorkflow';
import WorkflowDetail from './WorkflowDetail';

function WorkflowsPage() {
  return (
    <ErrorBoundary>
      <Route path="/workflows" exact component={WorkflowsList} />
      <Route
        path="/workflows/initiate"
        exact
        render={() => <Redirect to="/workflows/initiate/basic" />}
      />
      <Route
        path="/workflows/initiate/:step"
        exact
        render={(props: any) => <WorkflowsCreate {...props} isInitiate={true} />}
      />

      <Route path="/workflows/:id" exact component={WorkflowDetail} />
    </ErrorBoundary>
  );
}

export default WorkflowsPage;
