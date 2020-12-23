import React from 'react'

import styled from 'styled-components'
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary'
import { Route, Redirect } from 'react-router-dom'
import WorkflowsTable from './WorkflowsTable'
import WorkflowsCreate from './WorkflowsCreate'

const Container = styled.div`
  width: 100%;
`

function WorkflowsPage() {
  return (
    <ErrorBoundary>
      <Container>
        <Route path="/workflows" exact component={WorkflowsTable} />
        <Route
          path="/workflows/create"
          exact
          component={() => <Redirect to="/workflows/create/basic" />}
        />
        <Route path="/workflows/create/:step" component={WorkflowsCreate} />
      </Container>
    </ErrorBoundary>
  )
}

export default WorkflowsPage
