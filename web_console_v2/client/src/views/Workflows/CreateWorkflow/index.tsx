import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { Steps, Row, Card } from 'antd';
import StepOneBasic from './StepOneBasic';
import SteptTwoConfig from './SteptTwoConfig';
import { useSubscribe } from 'hooks';
import WORKFLOW_CHANNELS from './pubsub';
import { Prompt, Route, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const { Step } = Steps;

const FormArea = styled.main`
  margin-top: 12px;
`;
const StepContainer = styled.div`
  width: 350px;
`;

enum CreateSteps {
  basic,
  config,
}

export type WorkflowCreateProps = {
  isInitiate?: boolean;
  isAccept?: boolean;
};

const WorkflowsCreate: FC<WorkflowCreateProps> = (parentProps) => {
  const { t } = useTranslation();
  const params = useParams<{ step: keyof typeof CreateSteps; id?: string }>();
  const [currentStep, setStep] = useState(CreateSteps[params.step || 'basic']);

  useSubscribe(WORKFLOW_CHANNELS.go_config_step, () => {
    setStep(CreateSteps.config);
  });

  const createType = parentProps.isInitiate ? 'initiate' : `accept/${params.id}`;

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

      {/* TODO: avoid directly visit create/config, redirect user to basic */}
      <FormArea>
        <Route
          path={`/workflows/${createType}/basic`}
          exact
          render={(props) => <StepOneBasic {...props} {...parentProps} />}
        />
        <Route
          path={`/workflows/${createType}/config`}
          exact
          render={(props) => <SteptTwoConfig {...props} {...parentProps} />}
        />
      </FormArea>
    </>
  );
};

export default WorkflowsCreate;
