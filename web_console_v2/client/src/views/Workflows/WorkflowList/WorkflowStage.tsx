import StateIndicator from 'components/StateIndicator'
import React, { FC } from 'react'
import { getWorkflowStage } from 'shared/workflow'
import { Workflow } from 'typings/workflow'

const WorkflowStage: FC<{ data: Workflow }> = ({ data }) => {
  return <StateIndicator {...getWorkflowStage(data)} />
}

export default WorkflowStage
