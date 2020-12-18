import React, { ReactElement } from 'react'
import { Card } from 'antd'
import styled from 'styled-components'
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary'

const Container = styled.div`
  width: 100%;
`

function WorkflowsPage(): ReactElement {
  return (
    <ErrorBoundary>
      <Container>
        <Card />
      </Container>
    </ErrorBoundary>
  )
}

export default WorkflowsPage
