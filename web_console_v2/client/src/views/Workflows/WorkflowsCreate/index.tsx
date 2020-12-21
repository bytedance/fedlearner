import React from 'react'
import styled from 'styled-components'
import { Steps, Row, Card } from 'antd'
import WorkflowsCreateStepOne from './WorkflowsCreateStepOne'

const { Step } = Steps

const FormArea = styled.main`
  margin-top: 12px;
`

const StepContainer = styled.div`
  width: 350px;
`

function WorkflowsCreate() {
  return (
    <>
      <Card>
        <Row justify="center">
          <StepContainer>
            <Steps current={0}>
              <Step title="基础配置" />
              <Step title="工作流配置" />
            </Steps>
          </StepContainer>
        </Row>
      </Card>

      <FormArea>
        <WorkflowsCreateStepOne />
      </FormArea>
    </>
  )
}

export default WorkflowsCreate
