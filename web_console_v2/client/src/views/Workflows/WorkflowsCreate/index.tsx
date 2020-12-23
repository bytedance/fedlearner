import React, { useState } from 'react'
import styled from 'styled-components'
import { Steps, Row, Card } from 'antd'
import WorkflowsCreateStepOne from './StepOne'
import WorkflowsCreateStepTwo from './SteptTwo'
import { useSubscribe } from 'hooks'
import WORKFLOW_CHANNELS from './pubsub'
import { Prompt, Route, useParams, useHistory } from 'react-router-dom'

const { Step } = Steps

const FormArea = styled.main`
  margin-top: 12px;
`

const StepContainer = styled.div`
  width: 350px;
`

enum CreateSteps {
  basic,
  config,
}

function WorkflowsCreate() {
  const history = useHistory()
  const params = useParams<{ step: keyof typeof CreateSteps }>()
  const [currentStep, setStep] = useState(CreateSteps[params.step || 'basic'])

  useSubscribe(WORKFLOW_CHANNELS.go_config_step, () => {
    setStep(CreateSteps.config)
    history.push('/workflows/create/config')
  })

  return (
    <>
      {/* Route guards */}
      {process.env.NODE_ENV !== 'development' && (
        <Prompt when={true} message={'确定要离开吗，当前表单内容将全部丢失！'} />
      )}

      {/* Content */}
      <Card>
        <Row justify="center">
          <StepContainer>
            <Steps current={currentStep}>
              <Step title="基础配置" />
              <Step title="工作流配置" />
            </Steps>
          </StepContainer>
        </Row>
      </Card>

      <FormArea>
        <Route path={`/workflows/create/basic`} exact component={WorkflowsCreateStepOne} />
        {/* TODO: avoid directly visit create/config, redirect user to basic */}
        <Route path={`/workflows/create/config`} exact component={WorkflowsCreateStepTwo} />
      </FormArea>
    </>
  )
}

export default WorkflowsCreate
