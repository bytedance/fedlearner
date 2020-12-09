import React, { ReactElement, useEffect } from 'react'
import { Card } from 'antd'
import { useQuery } from 'react-query'
import { fetchExampleWorkflowTemplate } from 'services/workflow'

function WorkflowsPage(): ReactElement {
  const { isLoading, error, data } = useQuery('exampleTemplate', fetchExampleWorkflowTemplate)

  if (isLoading) return <div>Loading...</div>

  if (error) return <div>Error!</div>

  console.log(data)

  return (
    <div className="container">
      <Card>11</Card>
    </div>
  )
}

export default WorkflowsPage
