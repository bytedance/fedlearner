import React from 'react';

import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import { Route, Redirect } from 'react-router-dom';
import WorkflowsList from './WorkflowList';
import CreateWorkflow from './CreateWorkflow';
import ForkWorkflow from './ForkWorkflow';
import EditWorkflow from './EditWorkflow';
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
      {/* Coordinator initiate a worklflow */}
      <Route
        path="/workflows/initiate/:step"
        exact
        render={(props: any) => <CreateWorkflow {...props} isInitiate={true} />}
      />
      {/* Participant accept and fill the workflow config */}
      <Route
        path="/workflows/accept/:step/:id"
        exact
        render={(props: any) => <CreateWorkflow {...props} isAccept={true} />}
      />

      <Route
        path="/workflows/fork/:step/:id"
        exact
        render={(props: any) => <ForkWorkflow {...props} />}
      />

      <Route
        path="/workflows/edit/:step/:id"
        exact
        render={(props: any) => <EditWorkflow {...props} />}
      />

      <Route path="/workflows/:id" exact component={WorkflowDetail} />
    </ErrorBoundary>
  );
}

export default WorkflowsPage;
