import React, { ReactElement, useState } from 'react'
import { Card } from 'antd'
import { useQuery } from 'react-query'
import { fetchExampleWorkflowTemplate } from 'services/workflow'
import styled from 'styled-components'
import VariableSchemaForm from 'components/VariableSchemaForm'
import { buildFormFromJobDef } from 'shared/formSchema'
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary'

const Container = styled.div`
  width: 100%;
`

const DemoValueDisplay = styled.pre`
  display: block;
  background-color: #fff;
`

function WorkflowsPage(): ReactElement {
  const { isLoading, error, data: res } = useQuery('exampleTemplate', fetchExampleWorkflowTemplate)

  const [currentValue, setValue] = useState({})

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error!</div>

  const firstJob = res?.data.jobs[0]

  const firstJobFormSchema = buildFormFromJobDef(firstJob)

  return (
    <ErrorBoundary>
      <Container>
        <Card>
          <VariableSchemaForm schema={firstJobFormSchema} onConfirm={setValue} />
        </Card>
      </Container>

      <DemoValueDisplay>{JSON.stringify(currentValue)}</DemoValueDisplay>
    </ErrorBoundary>
  )
}

export default WorkflowsPage
