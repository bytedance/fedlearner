import React, { useState } from 'react'
import styled from 'styled-components'
import { Steps, Row, Card } from 'antd'
import WorkflowsCreateStepOne from './StepOneBasic'
import WorkflowsCreateStepTwo from './SteptTwoConfig'
import { useSubscribe } from 'hooks'
import WORKFLOW_CHANNELS from './pubsub'
import { Prompt, Route, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

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
  const { t } = useTranslation()
  const params = useParams<{ step: keyof typeof CreateSteps }>()
  const [currentStep, setStep] = useState(CreateSteps[params.step || 'basic'])

  useSubscribe(WORKFLOW_CHANNELS.go_config_step, () => {
    setStep(CreateSteps.config)
  })

  return (
    <>
      {/* Route guards */}
      {process.env.NODE_ENV !== 'development' && (
        <Prompt when={true} message={t('workflow.msg_sure_2_exist_create')} />
      )}

      {/* Content */}
      <Card>
        <Row justify="center">
          <StepContainer>
            <Steps current={currentStep}>
              <Step title={t('workflow.step_basic')} />
              <Step title={t('workflow.step_config')} />
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
