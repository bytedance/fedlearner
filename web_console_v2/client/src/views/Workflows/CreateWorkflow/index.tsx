import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { Steps, Row, Card } from 'antd';
import StepOneBasic from './StepOneBasic';
import SteptTwoConfig from './SteptTwoConfig';
import { Route, useHistory, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useUnmount } from 'react-use';
import { useResetCreateForms } from 'hooks/workflow';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';

const { Step } = Steps;

const StepContainer = styled.div`
  width: 350px;
`;
const FormArea = styled.section`
  flex: 1;
  margin-top: 12px;
  background-color: white;
`;

enum CreateSteps {
  basic,
  config,
}

export type WorkflowCreateProps = {
  // is Coordinator initaiting a workflow
  isInitiate?: boolean;
  // is Participant accepting a workflow from Coordinator
  isAccept?: boolean;
};

/**
 * NOTE: Workflow Creation actually has 2 situations:
 * 1. Coordinator initiate a workflow
 * 2. Participant accept and fill config of the workflow Coordinator initiated
 */
const WorkflowsCreate: FC<WorkflowCreateProps> = (workflowCreateProps) => {
  const { t } = useTranslation();
  const history = useHistory();
  const params = useParams<{ step: keyof typeof CreateSteps; id?: string }>();
  const [currentStep, setStep] = useState(CreateSteps[params.step || 'basic']);
  const reset = useResetCreateForms();

  useUnmount(() => {
    reset();
  });

  return (
    <SharedPageLayout
      title={<BackButton onClick={() => history.goBack()}>{t('menu.label_workflow')}</BackButton>}
      contentWrapByCard={false}
    >
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
        <Route
          path={`/workflows/initiate/basic`}
          exact
          render={(props) => (
            <StepOneBasic onSuccess={setToConfigStep} {...props} {...workflowCreateProps} />
          )}
        />
        <Route
          path={`/workflows/initiate/config`}
          exact
          render={(props) => <SteptTwoConfig {...props} {...workflowCreateProps} />}
        />
        <Route
          path={`/workflows/accept/basic/:id`}
          exact
          render={(props) => (
            <StepOneBasic onSuccess={setToConfigStep} {...props} {...workflowCreateProps} />
          )}
        />
        <Route
          path={`/workflows/accept/config/:id`}
          exact
          render={(props) => <SteptTwoConfig {...props} {...workflowCreateProps} />}
        />
      </FormArea>
    </SharedPageLayout>
  );

  function setToConfigStep() {
    setStep(CreateSteps.config);
  }
};

export default WorkflowsCreate;
