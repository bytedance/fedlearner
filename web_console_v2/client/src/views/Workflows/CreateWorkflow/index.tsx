import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { Steps, Row, Card } from 'antd';
import BreadcrumbLink from 'components/BreadcrumbLink';
import StepOneBasic from './StepOneBasic';
import SteptTwoConfig from './SteptTwoConfig';
import { useSubscribe } from 'hooks';
import WORKFLOW_CHANNELS from './pubsub';
import { Route, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const { Step } = Steps;

const FormArea = styled.section`
  flex: 1;
  margin-top: 12px;
  background-color: white;
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

/**
 * NOTE: Workflow Creation actually has 2 situations:
 * 1. Coordinator initiate a workflow
 * 2. Participant accept and fill config of the workflow Coordinator initiated
 */
const WorkflowsCreate: FC<WorkflowCreateProps> = (parentProps) => {
  const { t } = useTranslation();
  const params = useParams<{ step: keyof typeof CreateSteps; id?: string }>();
  const [currentStep, setStep] = useState(CreateSteps[params.step || 'basic']);

  useSubscribe(WORKFLOW_CHANNELS.go_config_step, () => {
    setStep(CreateSteps.config);
  });

  return (
    <>
      <BreadcrumbLink
        paths={[
          { label: 'menu.label_workflow', to: '/workflows' },
          { label: 'workflow.create_workflow' },
        ]}
      />

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
          path={`/workflows/initiate/basic`}
          exact
          render={(props) => <StepOneBasic {...props} {...parentProps} />}
        />
        <Route
          path={`/workflows/initiate/config`}
          exact
          render={(props) => <SteptTwoConfig {...props} {...parentProps} />}
        />
        <Route
          path={`/workflows/accept/basic/:id`}
          exact
          render={(props) => <StepOneBasic {...props} {...parentProps} />}
        />
        <Route
          path={`/workflows/accept/config/:id`}
          exact
          render={(props) => <SteptTwoConfig {...props} {...parentProps} />}
        />
      </FormArea>
    </>
  );
};

export default WorkflowsCreate;
