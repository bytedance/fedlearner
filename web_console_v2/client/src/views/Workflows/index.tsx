import React from 'react'

import ErrorBoundary from 'antd/lib/alert/ErrorBoundary'
import { Route, Redirect } from 'react-router-dom'
import WorkflowsTable from './WorkflowsTable'
import WorkflowsCreate from './WorkflowsCreate'

function WorkflowsPage() {
  return (
    <ErrorBoundary>
      <Route path="/workflows" exact component={WorkflowsTable} />
      <Route
        path="/workflows/create"
        exact
        component={() => <Redirect to="/workflows/create/basic" />}
      />
      <Route path="/workflows/create/:step" component={WorkflowsCreate} />
    </ErrorBoundary>
  )
}

export default WorkflowsPage
