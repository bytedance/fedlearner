import React from 'react';

import ErrorBoundary from 'components/ErrorBoundary';
import { Route, Redirect, useLocation } from 'react-router-dom';
import WorkflowsList from './WorkflowList';
import CreateWorkflow from './CreateWorkflow';
import ForkWorkflow from './ForkWorkflow';
import EditWorkflow from './EditWorkflow';
import WorkflowDetail from './WorkflowDetail';
import { WorkflowType } from 'typings/workflow';

function WorkflowsPage() {
  const location = useLocation();

  return (
    <ErrorBoundary>
      <Route
        path={`/workflow-center/workflows/list/:tabType(${WorkflowType.MY}|${WorkflowType.SYSTEM})`}
        exact
        component={WorkflowsList}
      />
      <Route
        path="/workflow-center/workflows/initiate"
        exact
        render={() => <Redirect to="/workflow-center/workflows/initiate/basic" />}
      />
      {/* Coordinator initiate a worklflow */}
      <Route
        path="/workflow-center/workflows/initiate/:step/:template_id?"
        exact
        render={(props: any) => <CreateWorkflow {...props} isInitiate={true} />}
      />
      {/* Participant accept and fill the workflow config */}
      <Route
        path="/workflow-center/workflows/accept/:step/:id"
        exact
        render={(props: any) => <CreateWorkflow {...props} isAccept={true} />}
      />

      <Route
        path="/workflow-center/workflows/fork/:step/:id"
        exact
        render={(props: any) => <ForkWorkflow {...props} />}
      />

      <Route
        path="/workflow-center/workflows/edit/:step/:id"
        exact
        render={(props: any) => <EditWorkflow {...props} />}
      />

      {location.pathname === '/workflow-center/workflows' && (
        <Redirect to={`/workflow-center/workflows/list/${WorkflowType.MY}`} />
      )}

      <Route path="/workflow-center/workflows/:id" exact component={WorkflowDetail} />
    </ErrorBoundary>
  );
}

export default WorkflowsPage;
