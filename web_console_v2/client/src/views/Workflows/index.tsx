import React, { ReactElement } from 'react'

import styled from 'styled-components'
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary'
import { Route } from 'react-router-dom'
import WorkflowsTable from './WorkflowsTable'
import WorkflowsCreate from './WorkflowsCreate'

const Container = styled.div`
  width: 100%;
`

function WorkflowsPage(props: any): ReactElement {
  return (
    <ErrorBoundary>
      <Container>
        <Route path="/workflows" exact component={WorkflowsTable} />
        <Route path="/workflows/create" exact component={WorkflowsCreate} />
      </Container>
    </ErrorBoundary>
  )
}

export default WorkflowsPage
